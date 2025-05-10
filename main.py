import pygame
import os
import sys
import heapq
import pytmx
import copy
from pytmx.util_pygame import load_pygame
import xml.etree.ElementTree as ET

# Initialize
pygame.init()
matrix = []
# Constants
WIDTH, HEIGHT = 1152, 768
PLAYER_SPEED = 3
SPRITE_SCALE = 2.5
MAP_SCALE = 2.5
TILE_SIZE = 16
SCALED_TILE_SIZE = int(TILE_SIZE * MAP_SCALE)
FPS = 60

# Setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Animated Player")


# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))


# Read and print layer 2 data directly from TMX file
tmx_path = os.path.join(script_dir, 'map check1.tmx')
tree = ET.parse(tmx_path)
root = tree.getroot()

# For "map check1.tmx", let's try to identify a suitable layer to use for pathfinding
# Look for layer with "road" in the name, or use a reasonable default
road_layer_name = None
for layer in root.findall('.//layer'):
    layer_name = layer.get('name', '')
    if 'road' in layer_name.lower():
        road_layer_name = layer_name
        break

# If no road layer found, use the first layer with data
if road_layer_name is None:
    for layer in root.findall('.//layer'):
        if layer.find('data') is not None:
            road_layer_name = layer.get('name')
            break

print(f"\nLoading map data from layer: {road_layer_name}")

# Extract data from the selected layer
matrix = []
for layer in root.findall(f'.//layer[@name="{road_layer_name}"]'):
    data = layer.find('data')
    if data is not None:
        # For chunked data with chunks
        chunks = layer.findall('data/chunk')
        if chunks:
            print(f"Map uses chunked data format with {len(chunks)} chunks")
            # Initialize a larger matrix to handle all chunks
            max_x, max_y = 0, 0
            min_x, min_y = 0, 0
            
            # First, determine the bounds of all chunks
            for chunk in chunks:
                chunk_x = int(chunk.get('x', 0))
                chunk_y = int(chunk.get('y', 0))
                chunk_width = int(chunk.get('width', 0))
                chunk_height = int(chunk.get('height', 0))
                
                min_x = min(min_x, chunk_x)
                min_y = min(min_y, chunk_y)
                max_x = max(max_x, chunk_x + chunk_width)
                max_y = max(max_y, chunk_y + chunk_height)
            
            # Create a matrix large enough to hold all chunks
            width = max_x - min_x
            height = max_y - min_y
            
            # Initialize with zeros
            matrix = [[0 for _ in range(width)] for _ in range(height)]
            
            print(f"Created matrix with dimensions: {width}x{height}")
            
            # Process first chunk only for simplicity
            chunk = chunks[0]
            if chunk is not None:
                chunk_x = int(chunk.get('x', 0))
                chunk_y = int(chunk.get('y', 0))
                chunk_width = int(chunk.get('width', 0))
                chunk_height = int(chunk.get('height', 0))
                
                # Process the chunk data
                chunk_data = chunk.text.strip().split(',')
                chunk_data = [x for x in chunk_data if x]
                
                # Fill in the part of the matrix that corresponds to this chunk
                for i in range(min(len(chunk_data), chunk_width * chunk_height)):
                    y = (i // chunk_width) + (chunk_y - min_y)
                    x = (i % chunk_width) + (chunk_x - min_x)
                    
                    if 0 <= y < height and 0 <= x < width:
                        try:
                            matrix[y][x] = int(chunk_data[i].strip()) if chunk_data[i].strip() else 0
                        except (ValueError, IndexError):
                            matrix[y][x] = 0
                
                print(f"Processed chunk at ({chunk_x},{chunk_y}) with size {chunk_width}x{chunk_height}")
        else:
            # Handle non-chunked data
            csv_data = data.text.strip().split(',')
            csv_data = [x for x in csv_data if x]
            width = int(layer.get('width'))
            for i in range(0, len(csv_data), width):
                row = csv_data[i:i+width]
                matrix.append(list(map(lambda s: int(s.strip()) if s.strip() else 0, row)))

if not matrix or len(matrix) == 0:
    print("Warning: Matrix is empty, creating a simple test matrix")
    # Create a simple test matrix if the map couldn't be parsed correctly
    matrix = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 128, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1]
    ]

temp = copy.deepcopy(matrix)

def ucs_algorithm(graph, start, target):
    # Safety check
    if not graph or len(graph) == 0 or len(graph[0]) == 0:
        print("Error: Invalid graph data")
        return []

    rows = len(graph)
    cols = len(graph[0])
    
    print(f"Graph dimensions: {rows}x{cols}")
    print(f"Start: {start}, Target value: {target}")
    
    # Safety check for start position
    if start[0] < 0 or start[0] >= rows or start[1] < 0 or start[1] >= cols:
        print(f"Error: Start position {start} out of bounds")
        return []
    
    # Directions for neighbors (up, down, left, right)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    # Priority queue for UCS (min-heap)
    pq = [(0, start[0], start[1])]  # (cost, x, y)
    
    # Initialize cost dictionary and visited set
    cost = {start: (0, None)}
    visited = set()

    def create_path(x, y):
        path = []
        while (x, y) != start:
            path.append((x, y))
            x, y = cost[(x, y)][1]
        path.append(start)
        return path[::-1]
    
    # Process the priority queue
    while pq:
        current_cost, x, y = heapq.heappop(pq)
        
        # If the target is reached, return
        if graph[x][y] == target:
            print(f"Found target at position ({x}, {y})")
            return create_path(x, y)
        
        if (x, y) in visited:
            continue
        
        visited.add((x, y))
        
        # Explore neighbors
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            
            # Check if the neighbor is within bounds
            if 0 <= nx < rows and 0 <= ny < cols and graph[nx][ny] != 0:
                new_cost = current_cost + 1
                
                # If the new cost is smaller, update and push to the queue
                if (nx, ny) not in visited and ((nx, ny) not in cost or new_cost < cost[(nx, ny)][0]):
                    cost[(nx, ny)] = (new_cost, (x, y))
                    heapq.heappush(pq, (new_cost, nx, ny))
    
    print("Warning: Target not found in graph")
    return []

# For demonstration, let's use simpler coordinates for start position
start_pos = (1, 1)
target_val = 128  # The target tile value to find

# Only attempt to find a path if the matrix has data
if matrix and len(matrix) > 0 and len(matrix[0]) > 0:
    try:
        path = ucs_algorithm(matrix, start_pos, target_val)
        print(f"Path found with {len(path)} steps")
        
        # Mark the path in the matrix
        for x, y in path:
            if 0 <= x < len(matrix) and 0 <= y < len(matrix[0]):
                matrix[x][y] = 128  # Mark the path
                
        # Update the TMX file (optional)
        # update_tmx_file(matrix)
    except Exception as e:
        print(f"Error finding path: {e}")
else:
    print("Cannot find path: Matrix is empty or invalid")

# Update the TMX file with modified matrix data

def update_tmx_file(matrix):
    for layer in root.findall('.//layer[@name="road2"]'):
        data = layer.find('data')
        if data is not None:
            # Convert matrix back to CSV format
            csv_data = []
            for row in matrix:
                csv_data.extend(map(str, row))
            data.text = ','.join(csv_data)
            # Save the modified TMX file
            tree.write(tmx_path)


# matrix = update_graph_with_path(matrix, (6,0) , 128)
# print(ucs_algorithm(matrix, (6,10) , 128))
for x, y in ucs_algorithm(matrix, (6,0) , 128):
    matrix[x][y] = 128

update_tmx_file(matrix)
print(matrix)


# Load the TMX map for the game
tmx_data = load_pygame(tmx_path)
player_sheet = pygame.image.load(os.path.join(script_dir, 'sprites', 'player-sheet.png'))

# Split sprite sheet into frames
def get_frames(sheet, frame_width, frame_height):
    frames = []
    for row in range(4):  # 4 directions
        frames_row = []
        for col in range(4):  # 4 frames per direction
            frame = sheet.subsurface(pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height))
            frames_row.append(frame)
        frames.append(frames_row)
    return frames

player_frames = get_frames(player_sheet, 12, 18)

# Directions
DIRECTION = {
    "down": 0,
    "left": 1,
    "right": 2,
    "up": 3
}

class Player:
    def __init__(self):
        self.width = 12 * SPRITE_SCALE
        self.height = 18 * SPRITE_SCALE
        self.x = 0 * SCALED_TILE_SIZE
        self.y = 6 * SCALED_TILE_SIZE
        self.speed = PLAYER_SPEED
        self.direction = "down"
        self.anim_index = 0
        self.frame_timer = 0
        self.frames = player_frames
        self.current_frames = self.frames[DIRECTION[self.direction]]

    def update(self, dt, keys):
        is_moving = False

        if keys[pygame.K_RIGHT]:
            self.x += self.speed
            self.direction = "right"
            is_moving = True
        elif keys[pygame.K_LEFT]:
            self.x -= self.speed
            self.direction = "left"
            is_moving = True
        elif keys[pygame.K_DOWN]:
            self.y += self.speed
            self.direction = "down"
            is_moving = True
        elif keys[pygame.K_UP]:
            self.y -= self.speed
            self.direction = "up"
            is_moving = True

        # Keep player within screen bounds
        self.x = max(0, min(WIDTH - self.width, self.x))
        self.y = max(0, min(HEIGHT - self.height, self.y))

        # Update animation
        self.current_frames = self.frames[DIRECTION[self.direction]]
        if is_moving:
            self.frame_timer += dt
            if self.frame_timer >= 0.2:
                self.frame_timer = 0
                self.anim_index = (self.anim_index + 1) % 4
        else:
            self.anim_index = 1

    def draw(self, surface):
        frame = self.current_frames[self.anim_index]
        scaled_frame = pygame.transform.scale(frame, (self.width, self.height))
        surface.blit(scaled_frame, (self.x, self.y))

# Map rendering class
class TiledMap:
    def __init__(self, tmx_data):
        self.tmx_data = tmx_data
        self.width = tmx_data.width * tmx_data.tilewidth
        self.height = tmx_data.height * tmx_data.tileheight
        
    def render(self, surface):
        for layer in self.tmx_data.visible_layers:
            if hasattr(layer, 'data'):
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        scaled_tile = pygame.transform.scale(tile, (SCALED_TILE_SIZE, SCALED_TILE_SIZE))
                        surface.blit(scaled_tile, (x * SCALED_TILE_SIZE, y * SCALED_TILE_SIZE))

# Initialize game elements
player = Player()
game_map = TiledMap(tmx_data)

# Main game loop
running = True
while running:
    # Calculate delta time
    dt = clock.tick(FPS) / 1000.0
    
    # Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
    
    # Get player input
    keys = pygame.key.get_pressed()
    player.update(dt, keys)
    
    # Render game
    screen.fill((0, 0, 0))
    game_map.render(screen)
    player.draw(screen)
    
    # Update display
    pygame.display.flip()

# Cleanup
pygame.quit()
sys.exit()
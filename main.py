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
tmx_path = os.path.join(script_dir, 'map', 'testmap.tmx')
tree = ET.parse(tmx_path)
root = tree.getroot()


print("\nLayer 2 Grid Data (Original TMX values):")
for layer in root.findall('.//layer[@name="road2"]'):
    data = layer.find('data')
    if data is not None:
        csv_data = data.text.strip().split(',')
        # Remove empty strings and convert to integers
        csv_data = [x for x in csv_data if x]
        # Print in grid format
        width = int(layer.get('width'))
        for i in range(0, len(csv_data), width):
            row = csv_data[i:i+width]
            matrix.append(list(map(lambda s: int(s.strip()), row)))
            # print(','.join(row))

temp = copy.deepcopy(matrix)

def ucs_algorithm(graph, start, target):
    rows = len(graph)
    cols = len(graph[0])
    
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
            return create_path(x, y)
        
        if (x, y) in visited:
            continue
        
        visited.add((x, y))
        
        # Explore neighbors
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            
            # Check if the neighbor is within bounds
            if 0 <= nx < rows and 0 <= ny < cols and matrix[nx][ny] != 0:
                new_cost = current_cost + 1
                
                # If the new cost is smaller, update and push to the queue
                if (nx, ny) not in visited and (nx, ny) not in cost or new_cost < cost[(nx, ny)][0]:
                    cost[(nx, ny)] = (new_cost, (x, y))
                    heapq.heappush(pq, (new_cost, nx, ny))
    
    return cost


def update_graph_with_path(graph, start, target):
    cost = ucs_algorithm(graph, start, target)
    
    # Trace back the path
    path = []
    x, y = start
    graph[x][y] = 128  # Mark the starting point
    
    while (x, y) != target:
        # Get the smallest neighbor cost
        min_cost = float('inf')
        next_x, next_y = -1, -1
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            
            if 0 <= nx < len(graph) and 0 <= ny < len(graph[0]):
                if cost.get((nx, ny), float('inf')) < min_cost:
                    min_cost = cost[(nx, ny)]
                    next_x, next_y = nx, ny
        
        # Move to the next node in the path
        x, y = next_x, next_y
        graph[x][y] = 128  # Mark the path with 128
    
    return graph





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
        self.x =  0 * SCALED_TILE_SIZE
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

# Create map instance
game_map = TiledMap(tmx_data)

# Game Loop
player = Player()
running = True

while running:
    dt = clock.tick(FPS) / 1000  # Delta time in seconds

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    player.update(dt, keys)

    # Clear screen
    screen.fill((0, 0, 0))
    
    # Draw map
    game_map.render(screen)
    
    # Draw player
    player.draw(screen)

    pygame.display.flip()

update_tmx_file(temp)
pygame.quit()
sys.exit()
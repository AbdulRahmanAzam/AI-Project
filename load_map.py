import pygame
import os
import sys
import xml.etree.ElementTree as ET
import psutil
import platform
import GPUtil
from datetime import datetime
import time

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1152, 768
TILE_SIZE = 64  # TMX file has 64x64 tilewidth/tileheight
MAP_SCALE = 0.5  # Scale down the map to fit on screen
SCALED_TILE_SIZE = int(TILE_SIZE * MAP_SCALE)
FPS = 144

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.frame_times = []
        self.max_samples = 60  # Store last 60 frames
        self.render_times = []
        self.visible_tiles = 0
        self.total_tiles = 0
        self.last_update = time.time()
        self.update_interval = 0.5  # Update stats every 0.5 seconds
        
    def add_frame_time(self, frame_time):
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_samples:
            self.frame_times.pop(0)
    
    def add_render_time(self, render_time):
        self.render_times.append(render_time)
        if len(self.render_times) > self.max_samples:
            self.render_times.pop(0)
    
    def get_stats(self):
        if not self.frame_times:
            return {
                'fps': 0,
                'frame_time': 0,
                'render_time': 0,
                'visible_tiles': 0,
                'total_tiles': 0,
                'tile_ratio': "0/0",
                'memory_usage': 0
            }
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        avg_render_time = sum(self.render_times) / len(self.render_times) if self.render_times else 0
        current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        return {
            'fps': current_fps,
            'frame_time': avg_frame_time * 1000,  # Convert to ms
            'render_time': avg_render_time * 1000,  # Convert to ms
            'visible_tiles': self.visible_tiles,
            'total_tiles': self.total_tiles,
            'tile_ratio': f"{self.visible_tiles}/{self.total_tiles}",
            'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024  # MB
        }

# Initialize performance monitor
perf_monitor = PerformanceMonitor()

# System Information
def get_system_info():
    info = {
        'os': f"{platform.system()} {platform.release()}",
        'cpu': platform.processor(),
        'cpu_cores': psutil.cpu_count(logical=False),
        'cpu_threads': psutil.cpu_count(logical=True),
        'ram': f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        'pygame_version': pygame.version.ver,
        'python_version': platform.python_version(),
        'resolution': f"{WIDTH}x{HEIGHT}",
        'start_time': datetime.now()
    }
    
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            info['gpu'] = f"{gpus[0].name} ({gpus[0].memoryTotal}MB)"
        else:
            info['gpu'] = "No GPU detected"
    except:
        info['gpu'] = "GPU info unavailable"
    
    return info

# Get system information
system_info = get_system_info()

# Setup the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Map Viewer - map check1.tmx")

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the map file
tmx_path = os.path.join(script_dir, 'map check1.tmx')

# Create a fallback tile (checkerboard pattern)
def create_fallback_tile(width, height, color1=(200, 200, 200), color2=(150, 150, 150)):
    surface = pygame.Surface((width, height))
    rect_size = width // 2
    for y in range(0, height, rect_size):
        for x in range(0, width, rect_size):
            color = color1 if (x // rect_size + y // rect_size) % 2 == 0 else color2
            pygame.draw.rect(surface, color, (x, y, rect_size, rect_size))
    return surface

# Create fallback tiles with different colors for different tilesets
fallback_tiles = {}

# Load the map directly using ElementTree for infinite maps
try:
    tree = ET.parse(tmx_path)
    root = tree.getroot()
    print(f"Successfully loaded map XML: {tmx_path}")
    
    # Get map properties
    map_width = int(root.get('width', 30))
    map_height = int(root.get('height', 20))
    tile_width = int(root.get('tilewidth', 64))
    tile_height = int(root.get('tileheight', 64))
    is_infinite = root.get('infinite', '0') == '1'
    
    print(f"Map size: {map_width}x{map_height} tiles (Infinite: {is_infinite})")
    print(f"Tile size: {tile_width}x{tile_height} pixels")
    
    # Count layers and tilesets
    layers = root.findall('.//layer')
    tilesets = root.findall('.//tileset')
    print(f"Number of layers: {len(layers)}")
    print(f"Number of tilesets: {len(tilesets)}")
    
    # Load tileset images
    tileset_images = {}
    for i, tileset in enumerate(tilesets):
        firstgid = int(tileset.get('firstgid', 1))
        tileset_width = int(tileset.get('tilewidth', 64))
        tileset_height = int(tileset.get('tileheight', 64))
        
        # Create a fallback tile for this tileset with a unique color
        hue = (i * 30) % 360
        # Convert HSV to RGB (simple approximation)
        h = hue / 60
        x = 1 - abs(h % 2 - 1)
        r, g, b = 0, 0, 0
        if 0 <= h < 1: r, g, b = 1, x, 0
        elif 1 <= h < 2: r, g, b = x, 1, 0
        elif 2 <= h < 3: r, g, b = 0, 1, x
        elif 3 <= h < 4: r, g, b = 0, x, 1
        elif 4 <= h < 5: r, g, b = x, 0, 1
        else: r, g, b = 1, 0, x
        
        color1 = (int(r*200), int(g*200), int(b*200))
        color2 = (int(r*150), int(g*150), int(b*150))
        fallback_tiles[firstgid] = create_fallback_tile(tileset_width, tileset_height, color1, color2)
        
        image_elem = tileset.find('.//image')
        if image_elem is not None:
            image_source = image_elem.get('source', '')
            print(f"Loading tileset {i+1}/{len(tilesets)}: {image_source}")
            
            # Extract the filename and construct a relative path
            filename = os.path.basename(image_source)
            
            # Look in several possible directories
            possible_paths = [
                os.path.join(script_dir, filename),
                os.path.join(script_dir, 'assets', filename),
                os.path.join(script_dir, 'tilemap 21 4', filename),
                os.path.join("C:", os.sep, "Users", "azama", "VS Code", "Python", "Ai Project", "ai-project", "tilemap 21 4", filename),
                os.path.join("C:", os.sep, "Users", "azama", "VS Code", "Python", "Ai Project", "ai-project", "assets", filename),
                image_source  # Try the full path as last resort
            ]
            
            image_loaded = False
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        print(f"Found tileset at: {path}")
                        tileset_images[firstgid] = {
                            'image': pygame.image.load(path),
                            'columns': int(tileset.get('columns', 1)),
                            'tilecount': int(tileset.get('tilecount', 1)),
                            'tilewidth': tileset_width,
                            'tileheight': tileset_height
                        }
                        image_loaded = True
                        break
                except Exception as e:
                    print(f"Failed to load image {path}: {e}")
            
            if not image_loaded:
                print(f"WARNING: Could not load tileset image for GID {firstgid}. Using fallback.")
                # Create a dummy tileset with the fallback tile
                tileset_images[firstgid] = {
                    'image': fallback_tiles[firstgid],
                    'columns': 1,
                    'tilecount': 1,
                    'tilewidth': tileset_width,
                    'tileheight': tileset_height,
                    'is_fallback': True
                }
    
    # Create a default fallback tile
    default_fallback = create_fallback_tile(tile_width, tile_height, (255, 0, 255), (200, 0, 200))
    
    # Function to get tile image by GID
    def get_tile_image(gid):
        if gid == 0:
            return None
        
        # Check for flip bits (Tiled stores flip in the high bits)
        # We'll ignore flipping for simplicity but extract the real GID
        FLIPPED_HORIZONTALLY_FLAG = 0x80000000
        FLIPPED_VERTICALLY_FLAG   = 0x40000000
        FLIPPED_DIAGONALLY_FLAG   = 0x20000000
        
        real_gid = gid & ~(FLIPPED_HORIZONTALLY_FLAG | FLIPPED_VERTICALLY_FLAG | FLIPPED_DIAGONALLY_FLAG)
        
        # Find the appropriate tileset
        tileset_gid = 0
        for first_gid in sorted(tileset_images.keys(), reverse=True):
            if real_gid >= first_gid:
                tileset_gid = first_gid
                break
                
        if tileset_gid == 0:
            return default_fallback
            
        tileset = tileset_images[tileset_gid]
        
        # If this is a fallback tileset, just return the fallback tile
        if tileset.get('is_fallback', False):
            return fallback_tiles.get(tileset_gid, default_fallback)
            
        # Get the local tile ID
        local_id = real_gid - tileset_gid
        
        # For very large GIDs, just return the fallback
        if local_id >= tileset['tilecount']:
            return fallback_tiles.get(tileset_gid, default_fallback)
        
        # Calculate position in the tileset
        columns = tileset['columns']
        tile_width = tileset['tilewidth']
        tile_height = tileset['tileheight']
        
        # Calculate the position in the tileset image
        x = (local_id % columns) * tile_width
        y = (local_id // columns) * tile_height
        
        # Create a subsurface from the tileset image
        try:
            rect = pygame.Rect(x, y, tile_width, tile_height)
            
            # Check if rect is within the image bounds
            if rect.right <= tileset['image'].get_width() and rect.bottom <= tileset['image'].get_height():
                return tileset['image'].subsurface(rect)
            else:
                # Return fallback if subsurface is out of bounds
                return fallback_tiles.get(tileset_gid, default_fallback)
                
        except Exception as e:
            # If there's an error, don't print it (too noisy) and just return a fallback
            return fallback_tiles.get(tileset_gid, default_fallback)
    
    # Process the chunk data from the map
    chunks = []
    for layer in layers:
        layer_name = layer.get('name', 'unnamed')
        layer_offset_x = int(layer.get('offsetx', 0))
        layer_offset_y = int(layer.get('offsety', 0))
        
        print(f"Processing layer: {layer_name}")
        data_elem = layer.find('data')
        
        if data_elem is not None:
            for chunk in data_elem.findall('chunk'):
                chunk_x = int(chunk.get('x', 0))
                chunk_y = int(chunk.get('y', 0))
                chunk_width = int(chunk.get('width', 16))
                chunk_height = int(chunk.get('height', 16))
                
                # Process the chunk data
                chunk_data = chunk.text.strip().split(',')
                chunk_data = [x.strip() for x in chunk_data if x.strip()]
                
                chunk_info = {
                    'layer': layer_name,
                    'x': chunk_x,
                    'y': chunk_y,
                    'width': chunk_width,
                    'height': chunk_height,
                    'data': [],
                    'offset_x': layer_offset_x,
                    'offset_y': layer_offset_y
                }
                
                # Convert data to grid
                for i in range(0, len(chunk_data), chunk_width):
                    if i + chunk_width <= len(chunk_data):
                        row = [int(val) if val else 0 for val in chunk_data[i:i+chunk_width]]
                        chunk_info['data'].append(row)
                
                chunks.append(chunk_info)
                print(f"  Processed chunk at ({chunk_x},{chunk_y}) with size {chunk_width}x{chunk_height}")
    
    print(f"Total chunks processed: {len(chunks)}")
    
except Exception as e:
    print(f"Error loading map: {e}")
    import traceback
    traceback.print_exc()
    pygame.quit()
    sys.exit(1)

# Initial camera position (center on a chunk)
if chunks:
    # Start at the first chunk
    first_chunk = chunks[0]
    camera_x = -first_chunk['x'] * SCALED_TILE_SIZE - first_chunk['offset_x'] * MAP_SCALE + WIDTH // 4
    camera_y = -first_chunk['y'] * SCALED_TILE_SIZE - first_chunk['offset_y'] * MAP_SCALE + HEIGHT // 4

# Camera parameters
camera_speed = 10
zoom = 1.0

# Font setup
font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 18)

# Main game loop
running = True
while running:
    frame_start = time.time()
    
    # Calculate delta time
    dt = clock.tick(FPS) / 1000.0
    
    # Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:  # Zoom in
                zoom = min(2.0, zoom + 0.1)
            elif event.key == pygame.K_MINUS:  # Zoom out
                zoom = max(0.2, zoom - 0.1)
    
    # Get keyboard input for camera movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        camera_x += camera_speed
    if keys[pygame.K_RIGHT]:
        camera_x -= camera_speed
    if keys[pygame.K_UP]:
        camera_y += camera_speed
    if keys[pygame.K_DOWN]:
        camera_y -= camera_speed
    
    # Clear screen
    screen.fill((30, 30, 30))  # Dark gray background
    
    # Render chunks
    current_effective_tile_size = int(SCALED_TILE_SIZE * zoom)
    render_start = time.time()
    visible_tiles = 0
    total_tiles = 0
    
    for chunk in chunks:
        chunk_x = chunk['x']
        chunk_y = chunk['y']
        chunk_data = chunk['data']
        layer_offset_x = chunk['offset_x'] * MAP_SCALE
        layer_offset_y = chunk['offset_y'] * MAP_SCALE
        
        # Calculate screen position of the chunk
        base_x = chunk_x * current_effective_tile_size + camera_x + layer_offset_x * zoom
        base_y = chunk_y * current_effective_tile_size + camera_y + layer_offset_y * zoom
        
        # Skip rendering if the entire chunk is offscreen
        if (base_x > WIDTH or 
            base_y > HEIGHT or 
            base_x + chunk['width'] * current_effective_tile_size < 0 or 
            base_y + chunk['height'] * current_effective_tile_size < 0):
            continue
        
        # Render each tile in the chunk
        for y, row in enumerate(chunk_data):
            for x, gid in enumerate(row):
                total_tiles += 1
                if gid > 0:  # Skip empty tiles
                    # Calculate screen position for this tile
                    screen_x = base_x + x * current_effective_tile_size
                    screen_y = base_y + y * current_effective_tile_size
                    
                    # Only draw tiles that are on or near screen
                    if (-current_effective_tile_size <= screen_x < WIDTH and 
                        -current_effective_tile_size <= screen_y < HEIGHT):
                        visible_tiles += 1
                        tile_image = get_tile_image(gid)
                        if tile_image:
                            # Scale the tile according to zoom
                            scaled_tile = pygame.transform.scale(
                                tile_image, 
                                (current_effective_tile_size, current_effective_tile_size)
                            )
                            screen.blit(scaled_tile, (screen_x, screen_y))
    
    render_time = time.time() - render_start
    perf_monitor.add_render_time(render_time)
    perf_monitor.visible_tiles = visible_tiles
    perf_monitor.total_tiles = total_tiles
    
    # Display system information
    y_offset = 10
    stats = perf_monitor.get_stats()
    
    info_lines = [
        f"OS: {system_info['os']}",
        f"CPU: {system_info['cpu']} ({system_info['cpu_cores']} cores, {system_info['cpu_threads']} threads)",
        f"GPU: {system_info['gpu']}",
        f"RAM: {system_info['ram']}",
        f"Python: {system_info['python_version']}",
        f"Pygame: {system_info['pygame_version']}",
        f"Resolution: {system_info['resolution']}",
        f"FPS: {stats['fps']:.1f}",
        f"Frame Time: {stats['frame_time']:.1f}ms",
        f"Render Time: {stats['render_time']:.1f}ms",
        f"Visible Tiles: {stats['tile_ratio']}",
        f"Memory Usage: {stats['memory_usage']:.1f} MB",
        f"Camera: ({-camera_x:.1f}, {-camera_y:.1f})",
        f"Zoom: {zoom:.1f}x",
        f"Tile Size: {current_effective_tile_size}px",
        f"Uptime: {(datetime.now() - system_info['start_time']).total_seconds():.1f}s"
    ]
    
    # Add performance warnings
    if stats['fps'] < 30:
        info_lines.append(f"WARNING: Low FPS! Consider reducing zoom or visible area")
    if stats['render_time'] > 16.67:  # More than 60 FPS worth of render time
        info_lines.append(f"WARNING: High render time! Rendering is taking too long")
    if stats['memory_usage'] > 500:  # More than 500MB
        info_lines.append(f"WARNING: High memory usage! Consider optimizing tile loading")
    
    for line in info_lines:
        text = small_font.render(line, True, (200, 200, 200))
        screen.blit(text, (10, y_offset))
        y_offset += 20
    
    # Controls info
    controls_text = font.render("Controls: Arrow keys to navigate, +/- to zoom, ESC to exit", True, (255, 255, 255))
    screen.blit(controls_text, (10, HEIGHT - 30))
    
    # Update display
    pygame.display.flip()
    
    # Update performance metrics
    frame_time = time.time() - frame_start
    perf_monitor.add_frame_time(frame_time)

# Cleanup
pygame.quit()
sys.exit() 

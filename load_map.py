import pygame
import os
import sys
import xml.etree.ElementTree as ET
import psutil
import platform
import GPUtil
from datetime import datetime
import time
import threading
from collections import OrderedDict

# Initialize Pygame
pygame.init()

# Get screen info
screen_info = pygame.display.Info()
SCREEN_WIDTH = screen_info.current_w
SCREEN_HEIGHT = screen_info.current_h

# Constants
WIDTH, HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT  # Use full screen dimensions
TILE_SIZE = 32  # TMX file has 64x64 tilewidth/tileheight
MAP_SCALE = 0.5  # Scale down the map to fit on screen
SCALED_TILE_SIZE = int(TILE_SIZE * MAP_SCALE)
FPS = 60
SHOW_DETAILS = False  # Initial state of details display
USE_HARDWARE_ACCELERATION = True
MAX_CACHE_SIZE = 50000  # Maximum number of tiles to cache
PRE_RENDERED_CHUNKS = 120  # Number of pre-rendered chunks
LAST_FRAMES = 120
FULLSCREEN = False  # Start in windowed mode

# Advanced caching system
class LRUCache:
    """Least Recently Used Cache with size limit"""
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
        
    def get(self, key):
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
        
    def put(self, key, value):
        if key in self.cache:
            # Move to end and update
            self.cache.move_to_end(key)
            self.cache[key] = value
        else:
            # Check if we need to remove oldest item
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)  # Remove least recently used
            self.cache[key] = value
    
    def clear(self):
        self.cache.clear()
        
    def __len__(self):
        return len(self.cache)
    
    def get_all_values(self):
        return list(self.cache.values())

# Multi-level cache system for different types of objects
tile_cache = LRUCache(MAX_CACHE_SIZE)  # Individual tile cache
chunk_cache = LRUCache(PRE_RENDERED_CHUNKS)   # Pre-rendered chunk cache

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.frame_times = []
        self.max_samples = LAST_FRAMES  # Store last 60 frames
        self.render_times = []
        self.visible_tiles = 0
        self.total_tiles = 0
        self.last_update = time.time()
        self.update_interval = 1.0    # Update stats every 1 second
        
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
                'memory_usage': 0,
                'cache_size': len(tile_cache),
                'cache_hits': tile_cache.hits,
                'cache_misses': tile_cache.misses,
                'chunk_cache_size': len(chunk_cache)
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
            'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            'cache_size': len(tile_cache),
            'cache_hits': tile_cache.hits,
            'cache_misses': tile_cache.misses,
            'chunk_cache_size': len(chunk_cache)
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
if FULLSCREEN:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
else:
    # Use 90% of screen size for windowed mode to ensure it fits
    windowed_width = int(WIDTH * 0.9)
    windowed_height = int(HEIGHT * 0.9)
    screen = pygame.display.set_mode((windowed_width, windowed_height), pygame.RESIZABLE)
    # Update WIDTH and HEIGHT to match the actual window size
    WIDTH, HEIGHT = windowed_width, windowed_height

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
            
            # Extract the filename and construct possible paths
            filename = os.path.basename(image_source)
            
            # Define possible directories to search
            possible_dirs = [
                script_dir,  # Current directory
                os.path.join(script_dir, 'assets'),
                os.path.join(script_dir, 'tilemap 21 4'),
                os.path.join(script_dir, 'Metal'),
                os.path.join(script_dir, 'Tile'),
                os.path.join(script_dir, 'Stone'),
                os.path.join(script_dir, 'Dirt'),
                os.path.join(script_dir, 'Wood'),
                os.path.join(script_dir, 'Plaster'),
                os.path.join(script_dir, 'Field'),
                os.path.join(script_dir, 'Elements'),
                os.path.join(script_dir, 'Brick')
            ]
            
            # Try to find the image in each possible directory
            image_loaded = False
            for directory in possible_dirs:
                possible_path = os.path.join(directory, filename)
                if os.path.exists(possible_path):
                    print(f"Found tileset at: {possible_path}")
                    try:
                        tileset_images[firstgid] = {
                            'image': pygame.image.load(possible_path),
                            'columns': int(tileset.get('columns', 1)),
                            'tilecount': int(tileset.get('tilecount', 1)),
                            'tilewidth': tileset_width,
                            'tileheight': tileset_height
                        }
                        image_loaded = True
                        break
                    except Exception as e:
                        print(f"Failed to load image {possible_path}: {e}")
            
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

# Create a toggle button for showing/hiding details
class ToggleButton:
    def __init__(self, x, y, width, height, text, font, active=True):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.active = active
        self.hover = False
        self.clicked = False
        
    def draw(self, surface):
        # Button background
        if self.active:
            color = (100, 200, 100) if not self.hover else (120, 220, 120)
        else:
            color = (200, 100, 100) if not self.hover else (220, 120, 120)
            
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2)  # Border
        
        # Button text
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def update(self, event_list):
        mouse_pos = pygame.mouse.get_pos()
        self.hover = self.rect.collidepoint(mouse_pos)
        
        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.hover:
                    self.clicked = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.clicked and self.hover:
                    self.active = not self.active
                    self.clicked = False
                    return True  # State changed
                self.clicked = False
        return False  # No state change

# Create toggle button
details_button = ToggleButton(10, 10, 120, 30, "Toggle Details", font, SHOW_DETAILS)

# Function to get a scaled tile, using cache when possible
def get_scaled_tile(gid, size):
    cache_key = (gid, size)
    cached_tile = tile_cache.get(cache_key)
    if cached_tile:
        return cached_tile
    
    tile_image = get_tile_image(gid)
    if tile_image:
        # Use pygame.transform.smoothscale for better quality when downscaling
        if size < tile_image.get_width():
            scaled_tile = pygame.transform.smoothscale(tile_image, (size, size))
        else:
            scaled_tile = pygame.transform.scale(tile_image, (size, size))
        
        tile_cache.put(cache_key, scaled_tile)
        return scaled_tile
    return None

# Pre-render a chunk to a surface for faster blitting
def render_chunk_to_surface(chunk, camera_x, camera_y, current_effective_tile_size, zoom):
    chunk_key = (chunk['x'], chunk['y'], current_effective_tile_size)
    cached_chunk = chunk_cache.get(chunk_key)
    if cached_chunk:
        return cached_chunk
    
    chunk_x = chunk['x']
    chunk_y = chunk['y']
    chunk_data = chunk['data']
    layer_offset_x = chunk['offset_x'] * MAP_SCALE
    layer_offset_y = chunk['offset_y'] * MAP_SCALE
    
    # Calculate chunk dimensions
    chunk_width = chunk['width'] * current_effective_tile_size
    chunk_height = chunk['height'] * current_effective_tile_size
    
    # Create a surface for this chunk
    chunk_surface = pygame.Surface((chunk_width, chunk_height), pygame.SRCALPHA)
    
    # Render tiles to the chunk surface
    for y, row in enumerate(chunk_data):
        for x, gid in enumerate(row):
            if gid > 0:  # Skip empty tiles
                # Calculate position within chunk surface
                tile_x = x * current_effective_tile_size
                tile_y = y * current_effective_tile_size
                
                # Get and blit the tile
                scaled_tile = get_scaled_tile(gid, current_effective_tile_size)
                if scaled_tile:
                    chunk_surface.blit(scaled_tile, (tile_x, tile_y))
    
    # Store in cache
    chunk_cache.put(chunk_key, chunk_surface)
    return chunk_surface

# Improved viewport culling
def is_chunk_visible(chunk_x, chunk_y, chunk_width, chunk_height, camera_x, camera_y):
    # Convert chunk coordinates to screen coordinates
    screen_x = chunk_x + camera_x
    screen_y = chunk_y + camera_y
    
    # Check if chunk is visible on screen
    return not (screen_x + chunk_width < 0 or 
                screen_x > WIDTH or 
                screen_y + chunk_height < 0 or 
                screen_y > HEIGHT)

# Get detailed memory usage information - only calculated when details are shown
def get_detailed_memory_info():
    if not SHOW_DETAILS:
        return {}  # Return empty dict if details are hidden
        
    memory_info = {
        'process_ram': psutil.Process().memory_info().rss / (1024 * 1024),  # MB
        'total_ram': psutil.virtual_memory().total / (1024 * 1024 * 1024),  # GB
        'used_ram': psutil.virtual_memory().used / (1024 * 1024 * 1024),    # GB
        'ram_percent': psutil.virtual_memory().percent,
        'swap_used': psutil.swap_memory().used / (1024 * 1024 * 1024),      # GB
        'swap_total': psutil.swap_memory().total / (1024 * 1024 * 1024),    # GB
        'swap_percent': psutil.swap_memory().percent,
        'tile_cache_count': len(tile_cache),
        'tile_cache_size': sum(tile.get_width() * tile.get_height() * 4 for tile in tile_cache.get_all_values()) / (1024 * 1024) if tile_cache.get_all_values() else 0  # Estimate in MB
    }
    
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            memory_info.update({
                'gpu_name': gpu.name
            })
    except:
        memory_info.update({
            'gpu_name': 'N/A'
        })
    
    return memory_info

# Main game loop
running = True
while running:
    frame_start = time.time()
    
    # Calculate delta time
    dt = clock.tick(FPS) / 1000.0
    
    # Process events
    event_list = pygame.event.get()
    for event in event_list:
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:  # Zoom in
                zoom = min(2.0, zoom + 0.1)
                # Clear cache when zoom changes
                chunk_cache.clear()
            elif event.key == pygame.K_MINUS:  # Zoom out
                zoom = max(0.2, zoom - 0.1)
                # Clear cache when zoom changes
                chunk_cache.clear()
            elif event.key == pygame.K_d:  # Toggle details with keyboard
                SHOW_DETAILS = not SHOW_DETAILS
            elif event.key == pygame.K_F11:  # Toggle fullscreen
                FULLSCREEN = not FULLSCREEN
                if FULLSCREEN:
                    # Save current position relative to screen size for proper repositioning
                    rel_camera_x = camera_x / WIDTH
                    rel_camera_y = camera_y / HEIGHT
                    # Switch to fullscreen
                    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
                    WIDTH, HEIGHT = SCREEN_WIDTH, SCREEN_HEIGHT
                    # Adjust camera position for new screen size
                    camera_x = rel_camera_x * WIDTH
                    camera_y = rel_camera_y * HEIGHT
                else:
                    # Save current position relative to screen size
                    rel_camera_x = camera_x / WIDTH
                    rel_camera_y = camera_y / HEIGHT
                    # Switch to windowed mode
                    windowed_width = int(SCREEN_WIDTH * 0.9)
                    windowed_height = int(SCREEN_HEIGHT * 0.9)
                    screen = pygame.display.set_mode((windowed_width, windowed_height), pygame.RESIZABLE)
                    WIDTH, HEIGHT = windowed_width, windowed_height
                    # Adjust camera position for new screen size
                    camera_x = rel_camera_x * WIDTH
                    camera_y = rel_camera_y * HEIGHT
        elif event.type == pygame.VIDEORESIZE:
            # Handle window resize events in windowed mode
            if not FULLSCREEN:
                WIDTH, HEIGHT = event.size
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    
    # Update button and check if details toggle changed
    if details_button.update(event_list):
        SHOW_DETAILS = details_button.active
    
    # Get keyboard input for camera movement
    keys = pygame.key.get_pressed()
    camera_moved = False
    if keys[pygame.K_LEFT]:
        camera_x += camera_speed
        camera_moved = True
    if keys[pygame.K_RIGHT]:
        camera_x -= camera_speed
        camera_moved = True
    if keys[pygame.K_UP]:
        camera_y += camera_speed
        camera_moved = True
    if keys[pygame.K_DOWN]:
        camera_y -= camera_speed
        camera_moved = True
    
    # Clear screen
    screen.fill((30, 30, 30))  # Dark gray background
    
    # Render chunks
    current_effective_tile_size = int(SCALED_TILE_SIZE * zoom)
    render_start = time.time()
    visible_tiles = 0
    total_tiles = 0
    
    # Sort chunks by layer for proper rendering order
    sorted_chunks = sorted(chunks, key=lambda c: c.get('layer', ''))
    
    for chunk in sorted_chunks:
        chunk_x = chunk['x']
        chunk_y = chunk['y']
        chunk_data = chunk['data']
        layer_offset_x = chunk['offset_x'] * MAP_SCALE
        layer_offset_y = chunk['offset_y'] * MAP_SCALE
        
        # Calculate screen position of the chunk
        base_x = chunk_x * current_effective_tile_size + camera_x + layer_offset_x * zoom
        base_y = chunk_y * current_effective_tile_size + camera_y + layer_offset_y * zoom
        
        # Skip rendering if the entire chunk is offscreen
        chunk_width = chunk['width'] * current_effective_tile_size
        chunk_height = chunk['height'] * current_effective_tile_size
        
        if not is_chunk_visible(base_x, base_y, chunk_width, chunk_height, 0, 0):
            continue
        
        # Render the chunk as a single surface
        chunk_surface = render_chunk_to_surface(chunk, camera_x, camera_y, current_effective_tile_size, zoom)
        screen.blit(chunk_surface, (base_x, base_y))
        
        # Count tiles for statistics
        if SHOW_DETAILS:
            for row in chunk_data:
                total_tiles += len(row)
                visible_tiles += sum(1 for gid in row if gid > 0)
    
    render_time = time.time() - render_start
    
    # Only update performance metrics if details are shown
    if SHOW_DETAILS:
        perf_monitor.add_render_time(render_time)
        perf_monitor.visible_tiles = visible_tiles
        perf_monitor.total_tiles = total_tiles
    
    # Draw the toggle button
    details_button.draw(screen)
    
    # Display system information if details are enabled
    if SHOW_DETAILS:
        y_offset = 50  # Start below the button
        stats = perf_monitor.get_stats()
        memory_info = get_detailed_memory_info()
        
        info_lines = [
            f"OS: {system_info['os']}",
            f"CPU: {system_info['cpu']} ({system_info['cpu_cores']} cores, {system_info['cpu_threads']} threads)",
            f"GPU: {system_info['gpu']}",
            f"RAM: {memory_info['used_ram']:.1f}/{memory_info['total_ram']:.1f} GB ({memory_info['ram_percent']}%)",
            f"Swap: {memory_info['swap_used']:.1f}/{memory_info['swap_total']:.1f} GB ({memory_info['swap_percent']}%)",
            f"Process Memory: {memory_info['process_ram']:.1f} MB",
            f"Rendering Mode: {'Hardware Accelerated' if USE_HARDWARE_ACCELERATION else 'Software'}",
            f"Python: {system_info['python_version']}",
            f"Pygame: {system_info['pygame_version']}",
            f"Resolution: {system_info['resolution']}",
            f"FPS: {stats['fps']:.1f}",
            f"Frame Time: {stats['frame_time']:.1f}ms",
            f"Render Time: {stats['render_time']:.1f}ms",
            f"Visible Tiles: {stats['tile_ratio']}",
            f"Tile Cache: {stats['cache_size']}/{MAX_CACHE_SIZE} (Hits: {stats['cache_hits']}, Misses: {stats['cache_misses']})",
            f"Chunk Cache: {stats['chunk_cache_size']}/{PRE_RENDERED_CHUNKS}",
            f"Camera: ({-camera_x:.1f}, {-camera_y:.1f})",
            f"Zoom: {zoom:.1f}x",
            f"Tile Size: {current_effective_tile_size}px",
            f"Uptime: {(datetime.now() - system_info['start_time']).total_seconds():.1f}s"
        ]
        
        for line in info_lines:
            text = small_font.render(line, True, (200, 200, 200))
            screen.blit(text, (10, y_offset))
            y_offset += 20
    else:
        # Just show minimal info when details are hidden
        minimal_info = font.render(f"FPS: {int(clock.get_fps())}", True, (200, 200, 200))
        screen.blit(minimal_info, (WIDTH - 100, 10))
    
    # Controls info always visible
    controls_text = font.render("Controls: Arrow keys to navigate, +/- to zoom, D to toggle details, F11 for fullscreen, ESC to exit", True, (255, 255, 255))
    screen.blit(controls_text, (10, HEIGHT - 30))
    
    # Update display
    pygame.display.flip()
    
    # Update performance metrics
    frame_time = time.time() - frame_start
    if SHOW_DETAILS:
        perf_monitor.add_frame_time(frame_time)

# Cleanup
pygame.quit()
sys.exit() 

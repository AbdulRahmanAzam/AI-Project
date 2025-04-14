import pygame
import os
import sys
import pytmx
from pytmx.util_pygame import load_pygame

# Initialize
pygame.init()

# Constants
WIDTH, HEIGHT = 1024, 768
PLAYER_SPEED = 3
SPRITE_SCALE = 2
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

# Load the TMX map
tmx_data = load_pygame(os.path.join(script_dir, 'map', 'testmap.tmx'))
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
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
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

pygame.quit()
sys.exit()

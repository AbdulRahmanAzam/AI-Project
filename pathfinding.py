import heapq

def is_walkable(tile_id):
    return tile_id != 0  # You can refine this check based on your actual road tile IDs.

def get_neighbors(x, y, width, height):
    directions = [(0, -1), (-1, 0), (1, 0), (0, 1)]
    neighbors = []

    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            neighbors.append((nx, ny))
    return neighbors

def find_path(tmx_data, start_pos, target_value):
    road_layer = tmx_data.get_layer_by_name("road2")
    width = tmx_data.width
    height = tmx_data.height

    visited = set()
    queue = []
    heapq.heappush(queue, (0, start_pos))
    came_from = {start_pos: None}

    while queue:
        cost, current = heapq.heappop(queue)

        if road_layer.data[current[1]][current[0]] == target_value:
            # Reconstruct path
            path = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        if current in visited:
            continue
        visited.add(current)

        for neighbor in get_neighbors(current[0], current[1], width, height):
            if neighbor not in visited:
                tile_id = road_layer.data[neighbor[1]][neighbor[0]]
                if is_walkable(tile_id) or tile_id == target_value:
                    new_cost = cost + 1
                    heapq.heappush(queue, (new_cost, neighbor))
                    if neighbor not in came_from:
                        came_from[neighbor] = current

    return None  # No path found

def visualize_path(tmx_data, path, path_tile_id=150):
    road_layer = tmx_data.get_layer_by_name("road2")
    
    for step in path:
        x, y = step
        # Avoid changing start or goal tile
        original_tile = road_layer.data[y][x]
        if original_tile not in [128, 130]:  # Avoid changing start/goal
            road_layer.data[y][x] = path_tile_id


import math
import random
import sys
import os
import asyncio
import traceback
import json
from dataclasses import dataclass

print("--- MAIN.PY STARTING! ---")

import pygame

def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v

def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

@dataclass
class Player:
    x: float
    y: float
    ang: float
    hp: int = 100
    ammo: int = 50
    medkits: int = 0
    grenades: int = 3
    weapon_idx: int = 0
    move_speed: float = 2.8
    rot_speed: float = 2.4

@dataclass
class Enemy:
    x: float
    y: float
    hp: int = 40
    max_hp: int = 40
    alive: bool = True
    cooldown: float = 0.0
    state: str = "idle"
    is_boss: bool = False
    scale: float = 1.0
    anim_timer: float = 0.0
    frame: int = 0
    subtype: str = "default"

@dataclass
class Particle:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    color: tuple
    life: float

@dataclass
class Item:
    x: float
    y: float
    type: str = "health" # "health" or "grenade"
    active: bool = True
    timer: float = 0.0

@dataclass
class Grenade:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    fuse: float
    bounced: int = 0

@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    is_player: bool = False
    life: float = 5.0

class World:
    def __init__(self, grid: list[str]) -> None:
        self.grid = grid
        self.h = len(grid)
        self.w = len(grid[0]) if self.h else 0

    def in_bounds(self, gx: int, gy: int) -> bool:
        return 0 <= gx < self.w and 0 <= gy < self.h

    def cell(self, gx: int, gy: int) -> str:
        if not self.in_bounds(gx, gy):
            return "#"
        if gx >= len(self.grid[gy]):
            return "#"
        return self.grid[gy][gx]

    def is_wall(self, gx: int, gy: int) -> bool:
        return self.cell(gx, gy) != "."

    def is_blocked(self, x: float, y: float) -> bool:
        return self.is_wall(int(x), int(y))

def try_move(world: World, x: float, y: float, nx: float, ny: float, radius: float) -> tuple[float, float]:
    def blocked(px: float, py: float) -> bool:
        for ox, oy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
            if world.is_blocked(px + ox, py + oy):
                return True
        return False

    tx, ty = x, y
    if not blocked(nx, ty):
        tx = nx
    if not blocked(tx, ny):
        ty = ny
    return tx, ty

def cast_ray_dda(world: World, ox: float, oy: float, ang: float, max_dist: float = 30.0) -> tuple[float, int, int, int]:
    dx = math.cos(ang)
    dy = math.sin(ang)
    map_x = int(ox)
    map_y = int(oy)
    delta_dist_x = abs(1.0 / dx) if dx != 0 else 1e30
    delta_dist_y = abs(1.0 / dy) if dy != 0 else 1e30

    if dx < 0:
        step_x = -1
        side_dist_x = (ox - map_x) * delta_dist_x
    else:
        step_x = 1
        side_dist_x = (map_x + 1.0 - ox) * delta_dist_x

    if dy < 0:
        step_y = -1
        side_dist_y = (oy - map_y) * delta_dist_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - oy) * delta_dist_y

    side = 0
    for _ in range(int(max_dist * 4) + 1):
        if side_dist_x < side_dist_y:
            side_dist_x += delta_dist_x
            map_x += step_x
            side = 0
        else:
            side_dist_y += delta_dist_y
            map_y += step_y
            side = 1

        if world.is_wall(map_x, map_y):
            if side == 0:
                perp = (map_x - ox + (1 - step_x) / 2) / (dx if dx != 0 else 1e-9)
            else:
                perp = (map_y - oy + (1 - step_y) / 2) / (dy if dy != 0 else 1e-9)
            return max(0.0001, perp), map_x, map_y, side

    return max_dist, map_x, map_y, side

def line_of_sight(world: World, x0: float, y0: float, x1: float, y1: float) -> bool:
    dx = x1 - x0
    dy = y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return True
    steps = max(1, int(dist * 12))
    for i in range(steps + 1):
        t = i / steps
        if world.is_blocked(x0 + dx * t, y0 + dy * t):
            return False
    return True

def load_anim(filepath) -> list[pygame.Surface]:
    frames = []
    import os
    img_dir = os.path.dirname(filepath)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    i = 0
    while True:
        frame_path = os.path.join(img_dir, f"{base_name}_f{i}.png")
        if os.path.exists(frame_path):
            try:
                surf = pygame.image.load(frame_path).convert_alpha()
                frames.append(surf)
            except Exception as e:
                print(f"Error loading {frame_path}: {e}")
            i += 1
        else:
            break
    return frames

def generate_textures():
    img_dir = os.path.join(os.path.dirname(__file__), "images")

    # --- Wall texture (fast) ---
    wall_tex = pygame.Surface((64, 64))
    wall_tex.fill((110, 55, 35))
    for y in range(0, 64, 16):
        pygame.draw.line(wall_tex, (60, 30, 15), (0, y), (64, y), 2)
    for i, x in enumerate(range(0, 64, 16)):
        off = 8 if (i % 2) else 0
        pygame.draw.line(wall_tex, (60, 30, 15), (x + off, 0), (x + off, 64), 2)
    for y in range(0, 64, 16):
        pygame.draw.line(wall_tex, (0,0,0), (0, y), (64, y), 2)
    for y in range(0, 64, 32):
        for x in range(0, 64, 16):
            pygame.draw.line(wall_tex, (0,0,0), (x, y), (x, y+16), 2)
        for x in range(8, 64, 16):
            pygame.draw.line(wall_tex, (0,0,0), (x, y+16), (x, y+32), 2)

    enemy_tex = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(enemy_tex, (200, 30, 40), (32, 28), 24)
    pygame.draw.circle(enemy_tex, (40, 0, 0), (22, 22), 6)
    pygame.draw.circle(enemy_tex, (40, 0, 0), (42, 22), 6)
    pygame.draw.circle(enemy_tex, (255, 200, 0), (22, 22), 2)
    pygame.draw.circle(enemy_tex, (255, 200, 0), (42, 22), 2)
    pygame.draw.rect(enemy_tex, (255, 255, 255), (20, 40, 24, 8), border_radius=2)

    gif_path = os.path.join(os.path.dirname(__file__), "images", "skeleton.gif")
    tex_enemy_frames = load_anim(gif_path)
    if not tex_enemy_frames: tex_enemy_frames = [enemy_tex]

    gif_boss = os.path.join(os.path.dirname(__file__), "images", "BOSS.gif")
    tex_boss_frames = load_anim(gif_boss)
    if not tex_boss_frames: tex_boss_frames = [enemy_tex]

    gif_death = os.path.join(os.path.dirname(__file__), "images", "Death.gif")
    tex_death_frames = load_anim(gif_death)
    if not tex_death_frames: tex_death_frames = [enemy_tex]

    # --- Floor/Ceiling textures (fast) ---
    floor_tex = pygame.Surface((64, 64))
    floor_tex.fill((55, 55, 55))
    for i in range(0, 64, 32):
        pygame.draw.line(floor_tex, (30, 30, 30), (0, i), (64, i), 2)
        pygame.draw.line(floor_tex, (30, 30, 30), (i, 0), (i, 64), 2)

    ceiling_tex = pygame.Surface((64, 64))
    ceiling_tex.fill((30, 30, 40))
    for i in range(0, 64, 16):
        pygame.draw.line(ceiling_tex, (50, 50, 60), (0, i), (64, i), 1)

    # --- Jungle textures (fast) ---
    wall_tex_jungle = pygame.Surface((64, 64))
    wall_tex_jungle.fill((35, 60, 25))
    for _ in range(8):
        vx = random.randint(0, 60)
        pygame.draw.rect(wall_tex_jungle, (20, 100, 20), (vx, 0, 4, 64))

    floor_tex_jungle = pygame.Surface((64, 64))
    floor_tex_jungle.fill((40, 80, 30))
    for _ in range(12):
        gx, gy = random.randint(0, 63), random.randint(32, 63)
        pygame.draw.line(floor_tex_jungle, (20, 150, 20), (gx, gy), (gx, gy - 8), 2)

    ceiling_tex_jungle = pygame.Surface((64, 64))
    ceiling_tex_jungle.fill((15, 35, 15))
    for _ in range(10):
        fx, fy = random.randint(0, 63), random.randint(0, 63)
        pygame.draw.circle(ceiling_tex_jungle, (10, 60, 10), (fx, fy), 5)

    gif_v2 = os.path.join(os.path.dirname(__file__), "images", "Slave nvl2.gif")
    tex_enemy_v2_frames = load_anim(gif_v2)
    if not tex_enemy_v2_frames: tex_enemy_v2_frames = [enemy_tex]

    gif_boss_v2 = os.path.join(os.path.dirname(__file__), "images", "Boss nvl2.gif")
    tex_boss_v2_frames = load_anim(gif_boss_v2)
    if not tex_boss_v2_frames: tex_boss_v2_frames = [enemy_tex]

    medkit_tex = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.rect(medkit_tex, (220, 220, 220), (16, 24, 32, 24), border_radius=4)
    pygame.draw.rect(medkit_tex, (200, 30, 30), (28, 28, 8, 16))
    pygame.draw.rect(medkit_tex, (200, 30, 30), (24, 32, 16, 8))
    pygame.draw.rect(medkit_tex, (100, 100, 100), (24, 18, 16, 6))

    gif_portal = os.path.join(img_dir, "portal.gif")
    tex_portal_frames = load_anim(gif_portal)
    if not tex_portal_frames: tex_portal_frames = [wall_tex]
    
    tex_portal_red_frames = []
    for f in tex_portal_frames:
        rf = f.copy()
        tint = pygame.Surface(f.get_size()).convert_alpha()
        tint.fill((255, 50, 50))
        rf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        tex_portal_red_frames.append(rf)

    key_tex = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(key_tex, (255, 215, 0), (32, 24), 12, 3)
    pygame.draw.rect(key_tex, (255, 215, 0), (30, 32, 4, 20))
    pygame.draw.rect(key_tex, (255, 215, 0), (34, 36, 8, 4))
    pygame.draw.rect(key_tex, (255, 215, 0), (34, 44, 8, 4))

    grenade_path = os.path.join(img_dir, "grenade.png")
    try:
        grenade_tex = pygame.image.load(grenade_path).convert_alpha()
        grenade_tex = pygame.transform.scale(grenade_tex, (64, 64))
    except:
        grenade_tex = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.circle(grenade_tex, (80, 100, 60), (32, 36), 18)
        pygame.draw.rect(grenade_tex, (50, 60, 40), (28, 16, 8, 10))
        pygame.draw.circle(grenade_tex, (180, 180, 180), (38, 18), 6, 2) # Pin ring

    def load_wep(idle_f, shoot_f, icon_f):
        try:
            idle = pygame.image.load(os.path.join(img_dir, idle_f)).convert_alpha()
            shoot = pygame.image.load(os.path.join(img_dir, shoot_f)).convert_alpha()
        except:
            idle = pygame.Surface((240, 240), pygame.SRCALPHA)
            shoot = pygame.Surface((240, 240), pygame.SRCALPHA)
        try:
            icon = pygame.image.load(os.path.join(img_dir, icon_f)).convert_alpha()
        except:
            icon = pygame.Surface((64, 32), pygame.SRCALPHA)
        return idle, shoot, icon

    p_idle, p_shoot, p_icon = load_wep("PistolIdle.png", "PistolShotting.png", "PistolPrint.png")
    s_idle, s_shoot, s_icon = load_wep("ShotgunIdle.png", "ShotgunShotting.png", "ShotgunPrint.png")

    return (wall_tex, tex_enemy_frames, tex_boss_frames, tex_death_frames, medkit_tex, p_idle, p_shoot, p_icon, s_idle, s_shoot, s_icon, floor_tex, ceiling_tex,
            wall_tex_jungle, tex_enemy_v2_frames, tex_boss_v2_frames, floor_tex_jungle, ceiling_tex_jungle, tex_portal_frames, tex_portal_red_frames, key_tex, grenade_tex)

class Game:
    def __init__(self) -> None:
        print("--- GAME INIT START ---")
        try:
            pygame.init()
            pygame.display.set_caption("Doom Pygame 2.5D")
        except Exception as e:
            print("Failed to init pygame:", e)

        self.W, self.H = 960, 540
        self.screen = pygame.display.set_mode((self.W, self.H))
        self.clock = pygame.time.Clock()
        try:
            self.font = pygame.font.SysFont("consolas", 18)
        except Exception:
            self.font = pygame.font.Font(None, 22)
        try:
            self.big_font = pygame.font.SysFont("consolas", 48, bold=True)
        except Exception:
            self.big_font = pygame.font.Font(None, 52)

        self.render_scale = 2 
        self.fov = math.radians(66)
        
        print("Generating textures...")
        (self.tex_wall_def, self.tex_enemy_def, self.tex_boss_def, self.tex_death_frames, self.tex_medkit, 
         self.p_idle, self.p_shoot, self.p_icon, self.s_idle, self.s_shoot, self.s_icon, self.tex_floor_def, self.tex_ceiling_def,
         self.tex_wall_jungle, self.tex_enemy_v2, self.tex_boss_v2, self.tex_floor_jungle, self.tex_ceiling_jungle,
         self.tex_portal, self.tex_portal_red, self.tex_key, self.tex_grenade) = generate_textures()
        print("Textures completed.")
        
        self.tex_wall = self.tex_wall_def
        self.tex_enemy_frames = self.tex_enemy_def
        self.tex_boss_frames = self.tex_boss_def
        self.tex_floor = self.tex_floor_def
        self.tex_ceiling = self.tex_ceiling_def
        
        self.player_has_key = False
        self.key_pos = None
        self.portal_pos = (2.5, 2.5)
        self.portal_frame = 0
        self.portal_timer = 0.0
        
        self.grenades_list: list[Grenade] = []
        self.grenade_throw_anim = 0.0
        self.items: list[Item] = []
        self.particles: list[Particle] = []
        self.projectiles: list[Projectile] = []
        self.wep_msg_timer = 0.0

        self.maps = [
            [
                "########################",
                "#......#...............#",
                "#..##..#..##...#####...#",
                "#......#.......#.......#",
                "#..#.......#...#..###..#",
                "#..#..###..#...#.......#",
                "#..#.......#...#####...#",
                "#......#...........#...#",
                "########..##########...#",
                "#......................#",
                "#......#.......#.......#",
                "########################",
            ],
            [
                "########################",
                "#......................#",
                "#..#.#..#.#..#.#..#.#..#",
                "#......................#",
                "#..#.#..##....##..#.#..#",
                "#..#.#..#......#..#.#..#",
                "#.......#......#.......#",
                "#..#.#..##....##..#.#..#",
                "#......................#",
                "#..#.#..#.#..#.#..#.#..#",
                "#......................#",
                "########################",
            ],
            [
                "########################",
                "#......................#",
                "#.####################.#",
                "#.#..................#.#",
                "#.#.################.#.#",
                "#.#.#..............#.#.#",
                "#.#.#.############.#.#.#",
                "#.#.#................#.#",
                "#.#.##################.#",
                "#.#....................#",
                "#..####################.",
                "########################",
            ],
            [
                "########################",
                "#..........##..........#",
                "#...####...##...####...#",
                "####..##........##..####",
                "#...####........##...###",
                "#..........##..........#",
                "#..###..########..###..#",
                "#..###..########..###..#",
                "#..........##..........#",
                "####..############..####",
                "#..........##..........#",
                "########################",
            ]
        ]
        self.map_idx = 0
        self.world = World(self.maps[self.map_idx])

        self.player = Player(x=1.5, y=1.5, ang=0.0)
        self.player_radius = 0.2
        self.enemies: list[Enemy] = []
        self.particles: list[Particle] = []
        self.items: list[Item] = []
        self.projectiles: list[Projectile] = []
        self.level = 0
        self.level_msg_timer = 0.0
        self._respawn_items()

        self.shake = 0.0
        self.weapon_t = 0.0
        self.firing = False
        self.fire_flash = 0.0
        self.hit_marker = 0.0
        # No browser, mouse grab is restricted; default to False for web compatibility
        import sys as _sys
        self.mouse_look = not getattr(_sys, 'platform', '').startswith('emscripten')
        self.heal_flash = 0.0
        self.moving_right = False
        
        self.game_state = "MENU"
        self.menu_options = ["INICIAR JOGO", "SALA PERSONALIZADA", "AMIGOS", "CRÉDITOS"]
        self.menu_selected = 0
        
        # Room Management
        self.custom_room_options = ["CRIAR SALA", "ENTRAR EM SALA"]
        self.custom_selected = 0
        self.room_code = ""
        self.input_text = "" # Texto sendo digitado
        self.is_host = False
        self.headshot_msg_timer = 0.0
        
        # Multiplayer: Gera ID único usando tempo + random para evitar colisões no navegador
        import time
        self.player_id = f"P{int(time.time() * 1000) % 100000}{random.randint(100, 999)}"
        self.other_players = {}
        self.network_task = None  # mantido para compatibilidade, não usado
        self.net_status = "DESCONECTADO"
        self.ws = None
        self.net_initialized = False  # Flag para o novo sistema de rede
        self.net_timer = 0.0
        self.net_packet_received = 0.0 # Timer para piscar bolinha de rede
        self.net_msg_count = 0 
        self.net_debug_logs = [] # Log de rede na tela
        
        self.mira_x = self.W // 2
        self.mira_y = self.H // 2
        self.pitch = 0
        
        print("Loading level for the first time...")
        self._next_level()
        self.level_msg_timer = 0.0

        # self._setup_mouse() # Removido do init para evitar erros de permissão do navegador
        print("--- GAME INIT COMPLETELY FINISHED ---")

    def _respawn_items(self):
        self.items = []
        free_spots = []
        for y in range(self.world.h):
            for x in range(self.world.w):
                if not self.world.is_wall(x, y):
                    free_spots.append((x + 0.5, y + 0.5))
        
        if free_spots:
            # Respawn Kits Medicos
            for _ in range(2 + self.level // 3):
                spot = random.choice(free_spots)
                self.items.append(Item(spot[0], spot[1], type="health"))
            
            # Respawn Granadas
            for _ in range(1 + self.level // 4):
                spot = random.choice(free_spots)
                self.items.append(Item(spot[0], spot[1], type="grenade"))
            
    def _get_map_colors(self):
        themes = [
            ((30, 25, 20), (20, 20, 30)),
            ((20, 50, 20), (10, 30, 10)), # Selva
            ((50, 30, 20), (30, 20, 20)),
            ((20, 10, 10), (50, 0, 0)),
        ]
        return themes[self.map_idx % len(themes)]

    def _next_level(self, target_map_idx=None):
        self.level += 1
        
        # FIX Crítico de Sincronização: Força o jogador temporariamente para a origem 
        # ANTES de calcular free_spots. Isso garante que a "zona morta" de 3.0 tiles
        # ao redor do jogador seja exatamente a mesma para Host e Client, 
        # resultando no MESMO ARRAY de free_spots, e consequentemente no mesmo spawn de inimigos!
        self.player.x, self.player.y = 1.5, 1.5
        
        # Sincroniza a semente (seed) do gerador de aleatoriedade usando a sala e nível atuais
        # Isso garante que inimigos e itens sejam spawnados exatamente nos mesmos lugares!
        if getattr(self, "room_code", ""):
            base_seed = self.level + sum(ord(c) for c in self.room_code)
            random.seed(base_seed)
            
        if self.level == 4:
            self.wep_msg_timer = 3.0
            self.player.ammo += 100
        
        should_switch = False
        if self.level == 6:
            should_switch = True
        elif self.level == 16:
            should_switch = True
        elif self.level > 16 and (self.level - 1) % 5 == 0:
            should_switch = True
            
        if target_map_idx is not None:
            if self.map_idx != target_map_idx:
                should_switch = True
                self.map_idx = target_map_idx
            else:
                should_switch = False
        elif should_switch:
            self.map_idx = (self.map_idx + 1) % len(self.maps)
            
        if should_switch:
            # Switch textures based on map
            if self.map_idx == 1:
                self.tex_wall = self.tex_wall_jungle
                self.tex_enemy_frames = self.tex_enemy_v2
                self.tex_boss_frames = self.tex_boss_v2
                self.tex_floor = self.tex_floor_jungle
                self.tex_ceiling = self.tex_ceiling_jungle
            else:
                self.tex_wall = self.tex_wall_def
                self.tex_enemy_frames = self.tex_enemy_def
                self.tex_boss_frames = self.tex_boss_def
                self.tex_floor = self.tex_floor_def
                self.tex_ceiling = self.tex_ceiling_def

            self.world = World(self.maps[self.map_idx % len(self.maps)])
            self.player.x, self.player.y = 1.5, 1.5
            self._respawn_items()

        self.player.hp = min(150, self.player.hp + 50)
        self.player.ammo += 100
        self.enemies = []
        self.projectiles = []
        self.level_msg_timer = 3.0

        target_subtype = "v2" if self.map_idx == 1 else "default"
        
        free_spots = []
        for gy in range(self.world.h):
            for gx in range(self.world.w):
                if not self.world.is_wall(gx, gy):
                    if math.hypot(gx + 0.5 - self.player.x, gy + 0.5 - self.player.y) > 3.0:
                        free_spots.append((gx + 0.5, gy + 0.5))
        
        is_boss_lvl = False
        if self.map_idx != 1 and self.level % 5 == 0:
            is_boss_lvl = True
        elif self.map_idx == 1 and self.level == 15:
            is_boss_lvl = True

        if is_boss_lvl:
            if free_spots:
                spot = random.choice(free_spots)
                prev_lvl = max(1, self.level - 1)
                prev_num_enemies = 4 + prev_lvl * 2
                prev_hp_val = 20 + prev_lvl * 20
                hp_val = int(3 * (prev_num_enemies * prev_hp_val))
                self.enemies.append(Enemy(spot[0], spot[1], hp=hp_val, max_hp=hp_val, is_boss=True, scale=2.2, subtype=target_subtype))
        else:
            num_enemies = 4 + self.level * 2
            for _ in range(num_enemies):
                if not free_spots: break
                spot = random.choice(free_spots)
                hp_val = 20 + self.level * 20
                scale_val = 0.4 if target_subtype == "v2" else 1.0
                self.enemies.append(Enemy(spot[0], spot[1], hp=hp_val, max_hp=hp_val, subtype=target_subtype, scale=scale_val))

        self.player_has_key = False
        self.key_pos = None
        
        # Posicionar Portal
        free_spots = []
        for gy in range(self.world.h):
            for gx in range(self.world.w):
                if not self.world.is_wall(gx, gy):
                    dist = math.hypot(gx + 0.5 - self.player.x, gy + 0.5 - self.player.y)
                    if dist > 6.0:
                        free_spots.append((gx + 0.5, gy + 0.5))
        if free_spots:
            self.portal_pos = random.choice(free_spots)
        else:
            self.portal_pos = (self.player.x, self.player.y)
            
        # Transmite aos clientes se avançou de nível durante o jogo
        if getattr(self, "is_host", False) and getattr(self, "game_state", "") == "PLAY":
            self.ws_send({
                "type": "start",
                "room": self.room_code,
                "map_idx": self.map_idx,
                "level": self.level
            })

    def _setup_mouse(self):
        try:
            pygame.event.set_grab(self.mouse_look)
        except Exception:
            pass
        try:
            pygame.mouse.set_visible(not self.mouse_look)
        except Exception:
            pass
        try:
            pygame.mouse.get_rel()
        except Exception:
            pass

    def toggle_mouse(self):
        self.mouse_look = not self.mouse_look
        self._setup_mouse()

    async def run(self):
        print("--- ASYNC RUN LOOP START ---")
        try:
            while True:
                dt = self.clock.tick(60) / 1000.0
                self._handle_events()
                
                # Rede: inicia e atualiza a cada frame (mais confiável que asyncio task)
                if self.room_code and self.game_state in ("LOBBY", "PLAY"):
                    self._net_tick()
                
                if self.game_state == "MENU":
                    self._render_menu()
                elif self.game_state == "CREDITS":
                    self._render_credits()
                elif self.game_state == "CUSTOM_ROOM":
                    self._render_custom_room()
                elif self.game_state == "FRIENDS":
                    self._render_friends()
                elif self.game_state == "JOIN_ROOM":
                    self._render_join_room()
                elif self.game_state == "LOBBY":
                    self._render_lobby()
                else:
                    self._update(dt)
                    self._render()
                
                # Envia posição se em jogo ou Lobby (Otimizado v9.0 - 10Hz)
                if self.game_state in ("LOBBY", "PLAY") and self.room_code and getattr(self, "ws", False):
                    self.net_timer += dt
                    # Reduzido para 10Hz (0.1s) para evitar travamentos em CPUs fracas
                    if self.net_timer > 0.1: 
                        self.net_timer = 0.0
                        self._send_pos()

                await asyncio.sleep(0)
        except Exception as e:
            print("FATAL ERROR IN RUN LOOP:", e)
            traceback.print_exc()

    def _net_init(self):
        """Inicializa o WebSocket no navegador (chamado uma vez ao entrar na sala)"""
        try:
            from platform import window
            window.eval(f"""
                console.log('[NET] Inicializando WebSocket...');
                if (window.doom_ws) window.doom_ws.close();
                
                let ws_protocol = (window.location.protocol === 'https:') ? 'wss://' : 'ws://';
                let ws_uri = ws_protocol + window.location.host + '/ws';
                
                window.doom_ws = new WebSocket(ws_uri);
                window.doom_msg_queue = [];
                window.doom_is_ready = false;
                window.doom_ws.onopen = () => {{
                    console.log('[NET] Conectado! Enviando JOIN para sala {self.room_code}...');
                    window.doom_is_ready = true;
                    window.doom_ws.send(JSON.stringify({{
                        type: 'join', room: '{self.room_code}', id: '{self.player_id}'
                    }}));
                }};
                window.doom_ws.onmessage = (e) => {{
                    const d = e.data;
                    if (window.doom_msg_queue.length > 20) window.doom_msg_queue.shift();
                    window.doom_msg_queue.push(d);
                }};
                window.doom_ws.onclose = (e) => {{
                    console.log('[NET] Desconectado. Code:', e.code);
                    window.doom_is_ready = false;
                }};
                window.doom_ws.onerror = (e) => {{
                    console.error('[NET] Erro WebSocket:', e);
                }};
            """)
            self.net_initialized = True
            self.net_status = "CONECTANDO..."
            self.net_debug_logs.append("NET: Init WS")
        except Exception as e:
            print(f"[NET] Init error (provavelmente desktop): {e}")

    def _net_tick(self):
        """Verifica e lê mensagens de rede a cada frame (modo síncrono, sem asyncio)"""
        try:
            from platform import window
            
            # Se não inicializado ou WebSocket fechou, reconecta
            if not self.net_initialized:
                self._net_init()
                return
            
            ws_state = window.eval("window.doom_ws ? window.doom_ws.readyState : -1")
            ws_state_int = int(ws_state) if ws_state is not None else -1
            
            # Estado 3 = CLOSED, -1 = sem WS. Reconecta.
            if ws_state_int == 3 or ws_state_int == -1:
                self.net_initialized = False
                self.ws = None
                self.net_status = "RECONECTANDO..."
                return
            
            # Estado 0 = CONNECTING
            if ws_state_int == 0:
                self.net_status = "CONECTANDO..."
                return
            
            # Estado 1 = OPEN
            if ws_state_int == 1:
                self.net_status = "CONECTADO"
                self.ws = True
            
            # Lê mensagens pendentes da fila JS de forma segura (Máximo 5 por frame para evitar travamentos)
            max_msgs = 5
            raw_msg = window.eval("window.doom_msg_queue ? window.doom_msg_queue.shift() : null")
            while raw_msg and max_msgs > 0:
                max_msgs -= 1
                try:
                    self.net_packet_received = 0.2
                    self.net_msg_count += 1
                    data = json.loads(str(raw_msg))
                    self._process_network_data(data)
                    # Log rápido (apenas se não estiver em jogo intenso)
                    if self.game_state != "PLAY":
                        m_type = data.get("type", "?")
                        if m_type != "pos":
                            self.net_debug_logs.append(f"REC: {m_type}")
                            if len(self.net_debug_logs) > 5: self.net_debug_logs.pop(0)
                except: pass
                if max_msgs > 0:
                    raw_msg = window.eval("window.doom_msg_queue ? window.doom_msg_queue.shift() : null")
        except:
            pass

    def _process_network_data(self, data):
        """Processa as mensagens que chegam do servidor"""
        msg_type = data.get("type")
        if msg_type == "pos":
            p_id = data.get("id")
            if p_id and p_id != self.player_id:
                self.other_players[p_id] = {
                    "x": data.get("x", 1.5), "y": data.get("y", 1.5), "ang": data.get("ang", 0)
                }
            
            # AUTO-REPARO: Se o Host enviou mapa/level e eu ainda não estou sincronizado, força entrada
            if not getattr(self, "is_host", False):
                h_level = data.get("level", 0)
                if h_level > self.level: # Só sincroniza se for um level MAIOR que o meu
                     self._process_network_data({"type": "start", "map_idx": data.get("map_idx",0), "level": h_level})

            if not getattr(self, "is_host", False) and "en" in data:
                for i, enc in enumerate(data.get("en", [])):
                    if i < len(self.enemies) and self.enemies[i].state != "dying":
                        self.enemies[i].x = enc[0]
                        self.enemies[i].y = enc[1]
                        self.enemies[i].hp = enc[2]
                        if self.enemies[i].state != "dying":
                            self.enemies[i].state = enc[3]
        elif msg_type == "player_joined":
            p_id = data.get("id")
            if p_id and p_id != self.player_id:
                print(f"[NET] Jogador entrou: {p_id}")
                if p_id not in self.other_players:
                    self.other_players[p_id] = {"x": 1.5, "y": 1.5, "ang": 0}
                
                # Se eu sou o HOST e o jogo já começou, aviso ao novo jogador
                if self.is_host and self.game_state == "PLAY":
                    self.ws_send({
                        "type": "start",
                        "room": self.room_code,
                        "map_idx": self.map_idx,
                        "level": self.level
                    })
        elif msg_type == "player_left":
            p_id = data.get("id")
            if p_id and p_id in self.other_players:
                print(f"[NET] Jogador saiu: {p_id}")
                del self.other_players[p_id]
        elif msg_type == "start":
            h_map = data.get("map_idx", 0)
            h_level = data.get("level", 1)
            self.net_debug_logs.append(f"START: M{h_map} L{h_level}")
            
            try:
                self.game_state = "PLAY"
                self.level = h_level - 1
                self._next_level(target_map_idx=h_map) # Agora o host dita qual o mapa correto!
                self.player.x, self.player.y = 1.5, 1.5
                self.net_debug_logs.append("STATE: PLAY OK")
            except Exception as e:
                self.net_debug_logs.append(f"ERR START: {str(e)[:15]}")
        elif msg_type == "portal_entered":
            if getattr(self, "is_host", False):
                # O cliente passou de fase, então o host avança todos!
                self._next_level()
        elif msg_type == "hit":
            idx = data.get("idx")
            dmg = data.get("dmg")
            if idx is not None and 0 <= idx < len(self.enemies):
                self.enemies[idx].hp -= dmg
                if self.enemies[idx].hp <= 0 and self.enemies[idx].alive:
                     self.enemies[idx].state = "dying"
                     self.enemies[idx].frame = 0
                     self.enemies[idx].anim_timer = 0.0
        elif msg_type == "grenade":
            # Outro jogador atirou uma granada
            self.grenades_list.append(Grenade(data["x"], data["y"], -0.2, data["vx"], data["vy"], -3.0, fuse=1.5))
        elif msg_type == "item":
            idx = data.get("idx")
            if idx is not None and 0 <= idx < len(self.items):
                 self.items[idx].active = False
                 self.items[idx].timer = 20.0


    def _send_pos(self):
        """Envia posição atual para o servidor via Bridge JS"""
        if getattr(self, "ws", False) and getattr(self, "room_code", ""):
            try:
                pack = {
                    "type": "pos", "room": self.room_code, "id": self.player_id,
                    "x": round(self.player.x, 2), "y": round(self.player.y, 2), "ang": round(self.player.ang, 2)
                }
                if getattr(self, "is_host", False):
                    pack["en"] = [[round(e.x, 2), round(e.y, 2), float(e.hp), e.state] for e in self.enemies]
                    pack["level"] = self.level
                    pack["map_idx"] = self.map_idx
                self.ws_send(pack)
            except:
                pass

    def ws_send(self, data_dict):
        """Ponte robusta v9.0 - JSON Direto para performance"""
        try:
            from platform import window
            msg_json = json.dumps(data_dict)
            # Evita eval() complexo, usa injeção simples
            window.eval(f"if(window.doom_ws&&window.doom_is_ready)window.doom_ws.send('{msg_json}');")
        except:
            pass

    def _render_menu(self):
        self.screen.fill((20, 20, 20))
        # Titulo Principal
        title = self.big_font.render("ULTIMATE DOOM 2.5D", True, (200, 30, 30))
        self.screen.blit(title, (self.W//2 - title.get_width()//2, 80))
        
        for i, option in enumerate(self.menu_options):
            color = (255, 255, 0) if i == self.menu_selected else (200, 200, 200)
            prefix = "> " if i == self.menu_selected else "  "
            txt = self.font.render(prefix + option, True, color)
            self.screen.blit(txt, (self.W//2 - txt.get_width()//2, 220 + i*50))
            
        pygame.display.flip()

    def _render_credits(self):
        self.screen.fill((15, 0, 0)) # Fundo infernal escuro
        
        # Titulo Principal
        title = self.big_font.render("--- DESENVOLVEDORES ---", True, (255, 40, 40))
        self.screen.blit(title, (self.W//2 - title.get_width()//2, 70))
        
        lines = [
            ("MATHEUS", "Mestre da Arquitetura 3D e Engenharia de Software"),
            ("EDUARDO", "Lorde do Design Visual e Vanguarda Criativa"),
            ("", ""),
            ("Uma experiência FPS forjada do zero.", ""),
            ("Feito com Sangue, Suor e Código.", ""),
            ("", ""),
            ("[ Pressione ESC para voltar ]", "")
        ]
        
        y = 170
        for name, desc in lines:
            if name and desc:
                txt1 = self.font.render(name + ": ", True, (255, 215, 0))
                txt2 = self.font.render(desc, True, (200, 200, 200))
                total_w = txt1.get_width() + txt2.get_width()
                self.screen.blit(txt1, (self.W//2 - total_w//2, y))
                self.screen.blit(txt2, (self.W//2 - total_w//2 + txt1.get_width(), y))
            elif name: # Somente texto centralizado (como o Pressione Esc)
                txt = self.font.render(name, True, (120, 120, 120))
                self.screen.blit(txt, (self.W//2 - txt.get_width()//2, y))
            y += 45
            
        pygame.display.flip()

    def _render_custom_room(self):
        self.screen.fill((10, 10, 30))
        title = self.big_font.render("SALA PERSONALIZADA", True, (100, 100, 255))
        self.screen.blit(title, (self.W//2 - title.get_width()//2, 80))
        
        for i, option in enumerate(self.custom_room_options):
            color = (255, 255, 0) if i == self.custom_selected else (200, 200, 200)
            prefix = "> " if i == self.custom_selected else "  "
            txt = self.font.render(prefix + option, True, color)
            self.screen.blit(txt, (self.W//2 - txt.get_width()//2, 220 + i*60))
            
        sub = self.font.render("[ Pressione ESC para voltar ]", True, (100, 100, 100))
        self.screen.blit(sub, (self.W//2 - sub.get_width()//2, self.H - 50))
        pygame.display.flip()

    def _render_join_room(self):
        self.screen.fill((10, 10, 30))
        title = self.big_font.render("ENTRAR EM SALA", True, (100, 255, 255))
        self.screen.blit(title, (self.W//2 - title.get_width()//2, 100))
        
        prompt = self.font.render("DIGITE O CÓDIGO DA SALA:", True, (255, 255, 255))
        self.screen.blit(prompt, (self.W//2 - prompt.get_width()//2, 220))
        
        # Caixa de Texto
        code_box = pygame.Surface((200, 50))
        code_box.fill((30, 30, 60))
        pygame.draw.rect(code_box, (0, 255, 255), (0, 0, 200, 50), 2)
        txt = self.big_font.render(self.input_text, True, (255, 255, 0))
        code_box.blit(txt, (100 - txt.get_width()//2, 0))
        self.screen.blit(code_box, (self.W//2 - 100, 270))
        
        sub = self.font.render("[ ENTER para Confirmar | ESC para Voltar ]", True, (150, 150, 150))
        self.screen.blit(sub, (self.W//2 - sub.get_width()//2, 400))
        pygame.display.flip()

    def _render_lobby(self):
        self.screen.fill((20, 40, 20))
        title = self.big_font.render("LOBBY DA SALA", True, (255, 255, 255))
        self.screen.blit(title, (self.W//2 - title.get_width()//2, 50))
        
        code_msg = self.font.render(f"CÓDIGO DA SALA: {self.room_code}", True, (255, 255, 0))
        self.screen.blit(code_msg, (self.W//2 - code_msg.get_width()//2, 120))

        id_msg = self.font.render(f"SEU ID: {self.player_id}", True, (200, 200, 200))
        self.screen.blit(id_msg, (self.W//2 - id_msg.get_width()//2, 150))
        
        status = self.font.render("AGUARDANDO JOGADORES...", True, (200, 200, 200))
        self.screen.blit(status, (self.W//2 - status.get_width()//2, 230))

        # Mostrar contagem de jogadores
        count = len(self.other_players) + 1
        players_txt = self.font.render(f"JOGADORES CONECTADOS: {count}", True, (0, 255, 0))
        self.screen.blit(players_txt, (self.W//2 - players_txt.get_width()//2, 280))
        
        # Lista os IDs dos outros
        for i, other_id in enumerate(self.other_players.keys()):
            id_txt = self.font.render(f" - {other_id}", True, (0, 200, 255))
            self.screen.blit(id_txt, (self.W//2 - id_txt.get_width()//2, 310 + i * 25))

        net_txt = self.font.render(f"REDE: {self.net_status} (Msgs: {self.net_msg_count})", True, (150, 150, 255))
        self.screen.blit(net_txt, (10, self.H - 30))
        
        
        if self.is_host:
            btn = self.font.render("[ PRESSIONE ENTER PARA INICIAR PARTIDA ]", True, (255, 255, 255))
            self.screen.blit(btn, (self.W//2 - btn.get_width()//2, 350))
        else:
            msg = self.font.render("O HOST INICIARÁ A PARTIDA EM BREVE", True, (150, 150, 150))
            self.screen.blit(msg, (self.W//2 - msg.get_width()//2, 350))

        sub = self.font.render("[ ESC para Sair ]", True, (100, 100, 100))
        self.screen.blit(sub, (self.W//2 - sub.get_width()//2, self.H - 50))
        pygame.display.flip()

    def _render_friends(self):
        self.screen.fill((10, 30, 10))
        title = self.big_font.render("LISTA DE AMIGOS", True, (100, 255, 100))
        self.screen.blit(title, (self.W//2 - title.get_width()//2, 100))
        msg = self.font.render("CONECTANDO AO SERVIDOR...", True, (255, 255, 255))
        self.screen.blit(msg, (self.W//2 - msg.get_width()//2, 250))
        sub = self.font.render("[ Pressione ESC para voltar ]", True, (150, 150, 150))
        self.screen.blit(sub, (self.W//2 - sub.get_width()//2, 350))
        pygame.display.flip()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
                
            if self.game_state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
                    elif event.key == pygame.K_DOWN:
                        self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        sel = self.menu_options[self.menu_selected]
                        if sel == "INICIAR JOGO":
                            self.game_state = "PLAY"
                            if self.mouse_look: self._setup_mouse()
                        elif sel == "SALA PERSONALIZADA":
                            self.game_state = "CUSTOM_ROOM"
                            self.custom_selected = 0
                        elif sel == "AMIGOS":
                            self.game_state = "FRIENDS"
                        elif sel == "CRÉDITOS":
                            self.game_state = "CREDITS"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    _, my = pygame.mouse.get_pos()
                    if 210 <= my < 260: # Iniciar Jogo
                        self.game_state = "PLAY"
                        if getattr(sys, 'platform', '').startswith('emscripten'): 
                            if not self.mouse_look: self.toggle_mouse()
                    elif 260 <= my < 310: # Sala Personalizada
                        self.game_state = "CUSTOM_ROOM"
                        self.custom_selected = 0
                    elif 310 <= my < 360: # Amigos
                        self.game_state = "FRIENDS"
                    elif 360 <= my <= 410: # Créditos
                        self.game_state = "CREDITS"

            elif self.game_state == "CUSTOM_ROOM":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.custom_selected = (self.custom_selected - 1) % len(self.custom_room_options)
                    elif event.key == pygame.K_DOWN:
                        self.custom_selected = (self.custom_selected + 1) % len(self.custom_room_options)
                    elif event.key == pygame.K_ESCAPE:
                        self.game_state = "MENU"
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        sel = self.custom_room_options[self.custom_selected]
                        if sel == "CRIAR SALA":
                            self.is_host = True
                            self.room_code = "".join([str(random.randint(0,9)) for _ in range(4)])
                            self.other_players = {}
                            self.game_state = "LOBBY"
                            # A task de rede será iniciada automaticamente no run()
                        elif sel == "ENTRAR EM SALA":
                            self.is_host = False
                            self.input_text = ""
                            self.other_players = {}
                            self.game_state = "JOIN_ROOM"

            elif self.game_state == "JOIN_ROOM":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = "CUSTOM_ROOM"
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        if len(self.input_text) > 0:
                            self.room_code = self.input_text
                            self.game_state = "LOBBY"
                            # A task de rede será iniciada automaticamente no run()
                    else:
                        if len(self.input_text) < 4 and event.unicode.isalnum():
                            self.input_text += event.unicode.upper()

            elif self.game_state == "LOBBY":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = "CUSTOM_ROOM"
                    if event.key == pygame.K_RETURN and self.is_host:
                        if self.ws: # Só deixa começar se estiver conectado!
                            self.game_state = "PLAY"
                            self._next_level() 
                        else:
                            print("[NET] Aguardando conexão para iniciar...")

            elif self.game_state in ("CREDITS", "FRIENDS"):
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    self.game_state = "MENU"
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.game_state = "MENU"
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: self.game_state = "MENU"
                    if event.key == pygame.K_m: self.toggle_mouse()
                    if event.key == pygame.K_1: self.player.weapon_idx = 0
                    if event.key == pygame.K_2 and self.level >= 4: self.player.weapon_idx = 1
                    if event.key == pygame.K_TAB: self._use_medkit()
                    if event.key == pygame.K_SPACE: self._throw_grenade()
                    if event.key == pygame.K_RETURN:
                        if getattr(self, "is_host", False) or not getattr(self, "room_code", ""):
                            self._next_level()
                        else:
                            if getattr(self, "ws", False):
                                self.ws_send({"type": "portal_entered", "room": self.room_code})
                            else:
                                self._next_level()
                    if event.key == pygame.K_r: self.player.ammo = min(200, self.player.ammo + 25)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if not self.mouse_look and getattr(sys, 'platform', '').startswith('emscripten'):
                        self.toggle_mouse()
                    self._fire()

    def _use_medkit(self):
        if self.player.hp < 150 and self.player.medkits > 0:
            self.player.medkits -= 1
            self.player.hp = min(150, self.player.hp + 30)
            self.heal_flash = 1.0

    def _update(self, dt: float):
        keys = pygame.key.get_pressed()

        self.level_msg_timer = max(0.0, self.level_msg_timer - dt)
        self.wep_msg_timer = max(0.0, self.wep_msg_timer - dt)
        self.headshot_msg_timer = max(0.0, self.headshot_msg_timer - dt)

        # Atualizar Partículas
        for p in self.particles[:]:
            p.life -= dt
            p.vz += 10.0 * dt # Gravidade
            p.z += p.vz * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.life <= 0 or p.z > 0.6: self.particles.remove(p)

        # Atualizar Projéteis
        for p in self.projectiles[:]:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            if p.life <= 0 or self.world.is_blocked(p.x, p.y):
                if p in self.projectiles: self.projectiles.remove(p)
                continue
            
            if not p.is_player:
                if math.hypot(p.x - self.player.x, p.y - self.player.y) < 0.4:
                    self.player.hp -= 15
                    self.shake = min(1.0, self.shake + 0.5)
                    if p in self.projectiles: self.projectiles.remove(p)

        alive_count = sum(1 for e in self.enemies if e.state != "dying" and e.alive)
        # self._next_level() removido para usar o sistema de Portal e Chave

        if self.mouse_look:
            mx, my = pygame.mouse.get_rel()
            self.player.ang = wrap_angle(self.player.ang + mx * 0.0022)
            self.pitch = clamp(self.pitch - my * 1.5, -self.H // 2, self.H // 2)
            self.mira_x = self.W // 2
            self.mira_y = self.H // 2
        else:
            rot = (1.0 if keys[pygame.K_LEFT] else 0) - (1.0 if keys[pygame.K_RIGHT] else 0)
            self.player.ang = wrap_angle(self.player.ang + rot * self.player.rot_speed * dt)
            self.mira_x = self.W // 2
            self.mira_y = self.H // 2
            self.pitch = 0

        move = pygame.Vector2()
        fw = pygame.Vector2(math.cos(self.player.ang), math.sin(self.player.ang))
        rt = pygame.Vector2(fw.y, -fw.x)
        if keys[pygame.K_w]: move += fw
        if keys[pygame.K_s]: move -= fw
        self.moving_right = bool(keys[pygame.K_d])
        if self.moving_right: move -= rt
        if keys[pygame.K_a]: move += rt

        speed = self.player.move_speed
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]: speed *= 1.4

        if move.length_squared() > 0:
            move = move.normalize() * speed * dt
            self.player.x, self.player.y = try_move(self.world, self.player.x, self.player.y, self.player.x + move.x, self.player.y + move.y, self.player_radius)

        if move.length_squared() > 0:
            self.weapon_t += dt * 6.0
        else:
            self.weapon_t = 0.0 # Reseta a animação ao parar

        self.shake = max(0.0, self.shake - dt * 6.0)
        self.fire_flash = max(0.0, self.fire_flash - dt * 3.5)
        self.hit_marker = max(0.0, self.hit_marker - dt * 8.0)
        self.heal_flash = max(0.0, self.heal_flash - dt * 3.0)
        self.grenade_throw_anim = max(0.0, self.grenade_throw_anim - dt)

        self._update_grenades(dt)

        # Animacao do Portal
        self.portal_timer += dt
        if self.portal_timer > 0.1:
            self.portal_timer = 0
            self.portal_frame = (self.portal_frame + 1) % len(self.tex_portal)

        # Coleta de Chave
        if self.key_pos:
            if math.hypot(self.player.x - self.key_pos[0], self.player.y - self.key_pos[1]) < 0.8:
                self.player_has_key = True
                self.key_pos = None

        # Colisao Portal
        if self.portal_pos:
            if math.hypot(self.player.x - self.portal_pos[0], self.player.y - self.portal_pos[1]) < 0.6:
                if self.player_has_key:
                    if getattr(self, "is_host", False) or not getattr(self, "room_code", ""):
                        self._next_level()
                    else:
                        # Cliente: avisa o Host para avançar de nível e remover a chave localmente
                        self.player_has_key = False
                        self.portal_pos = None
                        if getattr(self, "ws", False):
                            self.ws_send({"type": "portal_entered", "room": self.room_code})
                        else:
                            self._next_level()

        for p in self.particles[:]:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.z += p.vz * dt
            p.vz += 9.8 * dt
            p.life -= dt
            if p.life <= 0 or p.z > 0.5:
                self.particles.remove(p)

        px, py = self.player.x, self.player.y
        
        for it in self.items:
            if not it.active:
                it.timer -= dt
                if it.timer <= 0: it.active = True
            else:
                if math.hypot(it.x - px, it.y - py) < 0.6:
                    if it.type == "health":
                        if self.player.hp < 150:
                            self.player.hp = min(150, self.player.hp + 30)
                            self.heal_flash = 1.0 
                        else:
                            self.player.medkits += 1
                            self.heal_flash = 0.5 
                    elif it.type == "grenade":
                        self.player.grenades += 1
                        self.heal_flash = 0.5
                    it.active = False
                    it.timer = 20.0
                    
                    if getattr(self, "room_code", "") and getattr(self, "ws", False):
                        try:
                            idx = self.items.index(it)
                            self.ws_send({"type": "item", "room": self.room_code, "idx": idx})
                        except ValueError: pass

        for e in self.enemies:
            if not e.alive: continue
            
            if e.state == "dying":
                e.anim_timer += dt
                if e.anim_timer > 0.015:
                    e.anim_timer = 0.0
                    e.frame += 1
                    if e.frame >= len(self.tex_death_frames):
                        e.alive = False
                        # Se for um boss OU se for o último inimigo do nível, dropa a chave
                        alive_rem = sum(1 for en in self.enemies if en.alive and en.state != "dying")
                        if e.is_boss or alive_rem == 0:
                            self.key_pos = (e.x, e.y)
                continue

            # A IA só roda se for o Host OU se estiver jogando Sozinho (sem sala)
            is_effectively_host = getattr(self, "is_host", False) or not getattr(self, "room_code", "")
            if not is_effectively_host:
                if e.state == "chase":
                    e.anim_timer += dt
                    if e.is_boss:
                        if e.anim_timer > 0.02:
                            e.anim_timer = 0.0
                            e.frame = (e.frame + 1) % max(1, len(self.tex_boss_frames))
                    else:
                        anim_thresh = 0.06 if e.subtype == "v2" else 0.12
                        if e.anim_timer > anim_thresh:
                            e.anim_timer = 0.0
                            e.frame = (e.frame + 1) % max(1, len(self.tex_enemy_frames))
                continue

            e.cooldown = max(0.0, e.cooldown - dt)
            
            targets = [(px, py)]
            for pd in self.other_players.values():
                 targets.append((pd["x"], pd["y"]))
            
            best_t = targets[0]
            best_d = math.hypot(e.x - best_t[0], e.y - best_t[1])
            for t in targets[1:]:
                 d = math.hypot(e.x - t[0], e.y - t[1])
                 if d < best_d:
                     best_d, best_t = d, t
                     
            dx, dy = best_t[0] - e.x, best_t[1] - e.y
            dist = best_d

            if dist < 20.0 and line_of_sight(self.world, e.x, e.y, best_t[0], best_t[1]):
                e.state = "chase"
            elif dist > 25.0:
                e.state = "idle"

            if e.state == "chase" and dist > 1.2:
                e.anim_timer += dt
                if e.is_boss:
                    if e.anim_timer > 0.02:
                        e.anim_timer = 0.0
                        e.frame = (e.frame + 1) % max(1, len(self.tex_boss_frames))
                else:
                    anim_thresh = 0.06 if e.subtype == "v2" else 0.12
                    if e.anim_timer > anim_thresh:
                        e.anim_timer = 0.0
                        e.frame = (e.frame + 1) % max(1, len(self.tex_enemy_frames))

                vx, vy = dx / dist, dy / dist
                step = (1.5 if e.is_boss else 2.0) * dt
                nx, ny = e.x + vx * step, e.y + vy * step
                if not self.world.is_blocked(nx, ny):
                    e.x, e.y = nx, ny
                else: 
                    if not self.world.is_blocked(nx, e.y): e.x = nx
                    elif not self.world.is_blocked(e.x, ny): e.y = ny

            atk_dist = 4.5 if e.is_boss else 2.2
            if dist < atk_dist and e.cooldown <= 0.0 and line_of_sight(self.world, e.x, e.y, best_t[0], best_t[1]):
                # Habilidade Especial Boss nlv2: Tiro de Energia
                if e.is_boss and e.subtype == "v2" and dist > 3.0:
                    e.cooldown = 1.5
                    v_dir = pygame.Vector2(best_t[0] - e.x, best_t[1] - e.y).normalize() * 6.5
                    self.projectiles.append(Projectile(e.x, e.y, v_dir.x, v_dir.y))
                else:
                    e.cooldown = random.uniform(0.6, 1.1) if e.is_boss else random.uniform(0.7, 1.3)
                    if best_t == (px, py):
                        if random.random() < 0.55:
                            self.player.hp -= random.randint(15, 30) if e.is_boss else random.randint(2, 6)
                            self.shake = min(1.0, self.shake + (1.2 if e.is_boss else 0.6))

        if self.player.hp <= 0:
            self.player.x, self.player.y, self.player.ang = 2.5, 2.5, 0.0
            self.player.hp, self.player.ammo = 100, 50
            self.level = 0
            self._next_level()
            self.shake = self.fire_flash = 0.0

    def _use_medkit(self):
        if self.player.medkits > 0 and self.player.hp < 150:
            self.player.medkits -= 1
            self.player.hp = min(150, self.player.hp + 30)
            self.heal_flash = 1.0

    def _fire(self):
        is_shotgun = self.player.weapon_idx == 1
        ammo_cost = 2 if is_shotgun else 1
        
        if self.player.ammo < ammo_cost: return
        self.player.ammo -= ammo_cost
        self.fire_flash, self.shake = 1.0, min(1.0, self.shake + (0.5 if is_shotgun else 0.3))
        
        best, best_dist = None, 1e9
        px, py, pa = self.player.x, self.player.y, self.player.ang
        
        cam_x_mira = (2 * self.mira_x / self.W - 1.0)
        ang_mira = pa + math.atan(cam_x_mira * math.tan(self.fov / 2))
        
        sy_curr = (random.random()-0.5)*8*(self.shake**2)

        best, best_dist, best_headshot = None, 1e9, False
        for e in self.enemies:
            if not e.alive or e.state == "dying": continue
            dist = math.hypot(e.x - px, e.y - py)
            if dist < 0.25: continue
            
            tolerance = 0.08 if is_shotgun else 0.05
            rel_ang = wrap_angle(math.atan2(e.y - py, e.x - px) - ang_mira)
            
            if abs(rel_ang) <= tolerance:
                size = (self.H / dist)
                hh = size * 0.7 * e.scale
                # Hitbox agora acompanha o inimigo no chão
                top = (self.H + size) // 2 + sy_curr + self.pitch - hh
                bottom = top + hh
                
                if top <= self.mira_y <= bottom:
                    if line_of_sight(self.world, px, py, e.x, e.y):
                        if dist < best_dist:
                            best, best_dist = e, dist
                            # Headshot é o topo (cabeca) do sprite
                            best_headshot = self.mira_y <= top + hh * 0.25

        if best:
            if not is_shotgun:
                dmg = random.randint(20, 30)
            else:
                lvl_bonus = (self.level - 4) * 50
                dmg = random.randint(150, 220) + lvl_bonus
            
            if best_headshot:
                dmg *= 2
                self.headshot_msg_timer = 1.0

            best.hp -= dmg
            
            if getattr(self, "room_code", "") and getattr(self, "ws", False):
                try: 
                    idx = self.enemies.index(best)
                    self.ws_send({"type": "hit", "room": self.room_code, "idx": idx, "dmg": dmg})
                except ValueError:
                    pass
            
            self.hit_marker = 1.0
            p_count = 24 if best_headshot else 8
            for _ in range(p_count):
                # x, y, z, vx, vy, vz, color, life
                self.particles.append(Particle(best.x, best.y, 0.0, (random.random()-0.5)*2, (random.random()-0.5)*2, -random.random()*3, (200, 0, 0), 1.0))
            if best.hp <= 0:
                best.state = "dying"
                best.frame = 0
                best.anim_timer = 0.0

    def _render(self):
        bob = math.sin(self.weapon_t) * 2.5 + math.sin(self.weapon_t * 0.5) * 1.5
        sx, sy = (random.random()-0.5)*10*(self.shake**2), (random.random()-0.5)*8*(self.shake**2)
        px, py, pa = self.player.x, self.player.y, self.player.ang

        horizon = self.H // 2 + self.pitch
        floor_clr, ceil_clr = self._get_map_colors()
        pygame.draw.rect(self.screen, ceil_clr, (0, 0, self.W, horizon))
        pygame.draw.rect(self.screen, floor_clr, (0, horizon, self.W, self.H - horizon))

        # Fast flat floor/ceiling for browser compatibility
        floor_clr_full = floor_clr
        ceil_clr_full = ceil_clr
        # Draw ceiling
        pygame.draw.rect(self.screen, ceil_clr_full, (0, 0, self.W, int(horizon)))
        # Draw floor
        pygame.draw.rect(self.screen, floor_clr_full, (0, int(horizon), self.W, self.H - int(horizon)))

        cols = self.W // self.render_scale
        zbuf = [999.0] * cols

        for col in range(cols):
            cam_x = (2 * col / max(1, cols - 1) - 1.0)
            ray_ang = pa + math.atan(cam_x * math.tan(self.fov / 2))
            dist, mx, my, side = cast_ray_dda(self.world, px, py, ray_ang, max_dist=32.0)
            wd = dist * math.cos(ray_ang - pa)
            zbuf[col] = wd
            
            wh = int(self.H / max(0.0001, wd))
            y0, x0 = (self.H - wh) // 2 + int(sy) + self.pitch, col * self.render_scale + int(sx)

            hx, hy = px + dist * math.cos(ray_ang), py + dist * math.sin(ray_ang)
            tex_x = int((hy - my if side == 0 else hx - mx) * 64) % 64
            strip = self.tex_wall.subsurface((tex_x, 0, 1, 64))
            
            shade = max(0.1, 1.0 - wd / 12.0)
            if side == 1: shade *= 0.7
            if shade < 1.0:
                overlay = pygame.Surface((1, 64))
                overlay.fill((0, 0, 0))
                overlay.set_alpha(int((1-shade)*255))
                strip = strip.copy()
                strip.blit(overlay, (0,0))
                
            scale_strip = pygame.transform.scale(strip, (self.render_scale + 1, wh))
            self.screen.blit(scale_strip, (x0, y0))

        sprites = [(math.hypot(e.x-px, e.y-py), e.x, e.y, e) for e in self.enemies if e.alive]
        if self.key_pos:
            sprites.append((math.hypot(self.key_pos[0]-px, self.key_pos[1]-py), self.key_pos[0], self.key_pos[1], "key"))
        if self.portal_pos:
            sprites.append((math.hypot(self.portal_pos[0]-px, self.portal_pos[1]-py), self.portal_pos[0], self.portal_pos[1], "portal"))
        
        # Adicionar as Granadas Voadoras
        for g in self.grenades_list:
            sprites.append((math.hypot(g.x-px, g.y-py), g.x, g.y, g))
        
        sprites += [(math.hypot(p.x-px, p.y-py), p.x, p.y, p) for p in self.particles]
        sprites += [(math.hypot(p.x-px, p.y-py), p.x, p.y, p) for p in self.projectiles]
        sprites += [(math.hypot(it.x-px, it.y-py), it.x, it.y, it) for it in self.items if it.active]
        
        for p_id, p_data in self.other_players.items():
            sprites.append((math.hypot(p_data["x"]-px, p_data["y"]-py), p_data["x"], p_data["y"], "player"))

        sprites.sort(key=lambda t: -t[0])

        for dist, ex, ey, obj in sprites:
            rel = wrap_angle(math.atan2(ey - py, ex - px) - pa)
            # A profundidade para o Z-buffer deve ser a distância perpendicular (corrigida)
            sprite_wd = dist * math.cos(rel)
            
            # FIX CRÍTICO: Previne ZeroDivisionError e OutOfMemory ao tentar renderizar coisas muito perto
            if dist < 0.2: continue
            
            if abs(rel) > self.fov * 0.8: continue

            pt_x = (0.5 + rel / self.fov) * self.W + sx
            size = (self.H / dist)
            if isinstance(obj, (Enemy, Item, Grenade)) or obj in ("key", "portal", "player"):
                if isinstance(obj, Enemy):
                    scale = obj.scale
                    if obj.state == "dying":
                        f_idx = min(obj.frame, max(0, len(self.tex_death_frames) - 1))
                        tex = self.tex_death_frames[f_idx]
                    elif obj.is_boss:
                        f_idx = obj.frame % max(1, len(self.tex_boss_frames))
                        tex = self.tex_boss_frames[f_idx]
                    else:
                        f_idx = obj.frame % max(1, len(self.tex_enemy_frames))
                        tex = self.tex_enemy_frames[f_idx]
                elif isinstance(obj, Item):
                    tex = self.tex_medkit if obj.type == "health" else self.tex_grenade
                    scale = 0.8 if obj.type == "grenade" else 1.0
                elif isinstance(obj, Grenade):
                    tex = self.tex_grenade
                    scale = 0.4
                    z_off = (obj.z - 0.5)
                elif obj == "key":
                    tex = self.tex_key
                    scale = 0.5
                elif obj == "portal":
                    f_idx = self.portal_frame % len(self.tex_portal)
                    tex = self.tex_portal[f_idx] if self.player_has_key else self.tex_portal_red[f_idx]
                    scale = 2.0
                elif obj == "player":
                    # Recria a skin do jogador sempre (para evitar bugs de cache em trocas de mapa)
                    base_surf = getattr(self, "tex_enemy_frames", [None])[0]
                    if base_surf:
                        self.tex_player_cache = base_surf.copy()
                        tint = pygame.Surface(self.tex_player_cache.get_size(), pygame.SRCALPHA)
                        tint.fill((0, 255, 100, 160)) # Verde vibrante
                        self.tex_player_cache.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
                        tex = self.tex_player_cache
                    else:
                        tex = self.tex_wall # Fallback
                    scale = 0.8
                
                hw, hh = size * 0.7 * scale, size * 0.7 * scale
                if hw < 1 or hh < 1: continue
                # Posiciona o sprite no chão ao invés de centralizado no horizonte
                # Se for granada voadora, adiciona o deslocamento Z
                top = (self.H + size) // 2 + sy + self.pitch - hh + (size * 0.05)
                if isinstance(obj, Grenade):
                    top += z_off * size
                left = pt_x - hw / 2


                x_start, x_end = int(left), int(left + hw)
                
                if x_start >= self.W or x_end < 0: continue
                scaled_tex = pygame.transform.scale(tex, (int(hw), int(hh)))
                
                for x in range(max(0, x_start), min(self.W, x_end)):
                    ci = x // self.render_scale
                    if 0 <= ci < cols and zbuf[ci] < sprite_wd: continue
                    tex_x = min(x - x_start, int(hw) - 1)
                    strip = scaled_tex.subsurface((tex_x, 0, 1, int(hh)))
                    self.screen.blit(strip, (x, int(top)))
                
                # Desenha TAG de Jogador acima da cabeça
                if obj == "player":
                    tag = self.font.render("PLAYER", True, (0, 255, 0))
                    self.screen.blit(tag, (pt_x - tag.get_width()//2, top - 20))

                if isinstance(obj, Enemy) and obj.state != "dying":
                    hp_ratio = max(0.0, obj.hp / obj.max_hp)
                    bar_w = int(hw * 0.8)
                    bar_h = max(2, int(size * 0.05))
                    bar_x = int(pt_x - bar_w / 2)
                    bar_y = int(top - bar_h - size * 0.05)
                    pygame.draw.rect(self.screen, (150, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                    if obj.hp > 0:
                        pygame.draw.rect(self.screen, (0, 200, 0), (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))

            elif isinstance(obj, Projectile):
                psize = max(4, int(size * 0.15))
                ptop = self.H / 2 + sy + self.pitch
                ci = int(pt_x) // self.render_scale
                if 0 <= ci < cols and dist < zbuf[ci]:
                    pygame.draw.circle(self.screen, (255, 255, 0), (int(pt_x), int(ptop)), psize)
                    pygame.draw.circle(self.screen, (255, 255, 255), (int(pt_x), int(ptop)), psize // 2)

            else: # Particle
                p = obj
                psize = max(2, int(size * 0.05))
                ptop = self.H / 2 + (p.z * size) + sy + self.pitch
                ci = int(pt_x) // self.render_scale
                if 0 <= ci < cols and dist < zbuf[ci]:
                    pygame.draw.rect(self.screen, (200, 20, 20), (pt_x, ptop, psize, psize))

        self._draw_weapon(bob, sx, sy)
        self._draw_hud()
        
        pad, s = 10, 6
        x0, y0 = self.W - self.world.w*s - pad, pad
        pygame.draw.rect(self.screen, (0,0,0), (x0-1, y0-1, self.world.w*s+2, self.world.h*s+2))
        for gy in range(self.world.h):
            for gx in range(self.world.w):
                if self.world.is_wall(gx, gy): pygame.draw.rect(self.screen, (160, 80, 80), (x0+gx*s, y0+gy*s, s, s))
        for e in self.enemies:
            if e.alive and e.state != "dying": 
                c = (255, 100, 0) if e.is_boss else (200, 40, 40)
                r = 4 if e.is_boss else 2
                pygame.draw.circle(self.screen, c, (x0+int(e.x*s), y0+int(e.y*s)), r)
        for it in self.items:
            if it.active: pygame.draw.circle(self.screen, (200, 200, 255), (x0+int(it.x*s), y0+int(it.y*s)), 2)
        
        # Minimapa: Desenha outros jogadores (AZUL)
        for p_data in self.other_players.values():
            pygame.draw.circle(self.screen, (0, 100, 255), (x0+int(p_data["x"]*s), y0+int(p_data["y"]*s)), 3)

        px_m, py_m = x0+int(px*s), y0+int(py*s)
        pygame.draw.circle(self.screen, (220, 220, 220), (px_m, py_m), 3)
        pygame.draw.line(self.screen, (220, 220, 220), (px_m, py_m), (px_m+int(math.cos(pa)*5), py_m+int(math.sin(pa)*5)), 2)
        
        if self.level % 5 == 0 and self.level_msg_timer > 0:
            msg = self.big_font.render("BOSS LEVEL!", True, (255, 0, 0))
            self.screen.blit(msg, (self.W//2 - msg.get_width()//2, self.H//3))

        pygame.display.flip()

    def _throw_grenade(self):
        if self.player.grenades > 0 and self.grenade_throw_anim <= 0:
            self.player.grenades -= 1
            self.grenade_throw_anim = 0.6
            spd = 8.0
            vx = math.cos(self.player.ang) * spd
            vy = math.sin(self.player.ang) * spd
            # z = -0.2 (mão), vz = -3.0 (arco mais baixo)
            self.grenades_list.append(Grenade(self.player.x, self.player.y, -0.2, vx, vy, -3.0, fuse=1.5))
            # Sincronização via Rede
            if getattr(self, "ws", False) and getattr(self, "room_code", ""):
                 self.ws_send({
                     "type": "grenade", "room": self.room_code,
                     "x": self.player.x, "y": self.player.y,
                     "vx": vx, "vy": vy
                 })

    def _update_grenades(self, dt):
        for g in self.grenades_list[:]:
            g.fuse -= dt
            # Gravidade e movimento vertical
            g.vz += 15.0 * dt
            g.z += g.vz * dt
            
            # Quicar no chão
            if g.z > 0.5:
                g.z = 0.5
                g.vz *= -0.4 # Perde energia ao quicar
                g.vx *= 0.8  # Atrito no chão
                g.vy *= 0.8
            
            # Movimento horizontal e colisão com paredes
            nx, ny = g.x + g.vx * dt, g.y + g.vy * dt
            if self.world.is_wall(int(nx), int(g.y)): g.vx *= -0.6
            else: g.x = nx
            if self.world.is_wall(int(g.x), int(ny)): g.vy *= -0.6
            else: g.y = ny
            
            g.vx *= 0.98; g.vy *= 0.98
            if g.fuse <= 0:
                self._explode(g.x, g.y)
                self.grenades_list.remove(g)

    def _explode(self, ex, ey):
        radius = 3.5
        damage = 300
        for e in self.enemies:
            if e.alive:
                d = math.hypot(e.x-ex, e.y-ey)
                if d < radius:
                    dmg = damage * (1.0 - d/radius)
                    e.hp -= dmg
                    
                    if getattr(self, "room_code", "") and getattr(self, "ws", False):
                        try:
                            idx = self.enemies.index(e)
                            self.ws_send({"type": "hit", "room": self.room_code, "idx": idx, "dmg": dmg})
                        except ValueError: pass
                        
                    if e.hp <= 0: e.state = "dying"; e.frame = 0
                    self.hit_marker = 0.5
        for _ in range(30):
            ang = random.random()*math.pi*2
            spd = random.uniform(2,8)
            # x, y, z, vx, vy, vz, color, life
            self.particles.append(Particle(ex, ey, 0.5, math.cos(ang)*spd, math.sin(ang)*spd, -random.uniform(3,7), (255, random.randint(50,150), 0), 1.2))
        self.shake = 1.8

    def _draw_weapon(self, bob, sx, sy):
        if self.player.weapon_idx == 0:
            tex_idle, tex_shoot = self.p_idle, self.p_shoot
        else:
            tex_idle, tex_shoot = self.s_idle, self.s_shoot
            
        tex = tex_shoot if self.fire_flash > 0.1 else tex_idle
        
        orig_w, orig_h = tex.get_size()
        if orig_h == 0: orig_h = 1
        
        # Reduzido de 0.7 para 0.5 para deixar a arma menor
        target_h = self.H * 0.5 
        target_w = orig_w * (target_h / orig_h)
        
        bx = int(math.cos(self.weapon_t) * 15)
        by = int(bob * 10)
        
        # Posicionamento lateral: Pistola mais à esquerda, Shotgun mais à direita
        offset_x = -60 if self.player.weapon_idx == 0 else -20
        x = (self.W - target_w) // 2 + bx + sx + offset_x
        
        # Reduzido o offset de 70 para 50 para mover mais para cima
        y = self.H - target_h + by + 50 + sy 
        
        scaled_tex = pygame.transform.scale(tex, (int(target_w), int(target_h)))
        self.screen.blit(scaled_tex, (int(x), int(y)))

        
    def _draw_hud(self):
        # Fundo do HUD semi-transparente
        hud_surface = pygame.Surface((self.W, 100), pygame.SRCALPHA)
        hud_surface.fill((0, 0, 0, 150))
        self.screen.blit(hud_surface, (0, self.H - 100))
        
        # --- BARRA DE VIDA (PREMIUM) ---
        hp_x, hp_y = 30, self.H - 70
        hp_w, hp_h = 250, 25
        pygame.draw.rect(self.screen, (50, 50, 50), (hp_x, hp_y, hp_w, hp_h), border_radius=5)
        hp_color = (40, 200, 40) if self.player.hp > 60 else (200, 200, 40) if self.player.hp > 30 else (200, 40, 40)
        hp_perc = max(0, min(1.0, self.player.hp / 150.0))
        pygame.draw.rect(self.screen, hp_color, (hp_x+2, hp_y+2, int((hp_w-4)*hp_perc), hp_h-4), border_radius=4)
        
        hp_text = self.font.render(f"HP: {int(self.player.hp)}", True, (255, 255, 255))
        self.screen.blit(hp_text, (hp_x + 10, hp_y - 25))

        # --- NÍVEL DO MAPA ---
        lvl_text = self.font.render(f"NÍVEL: {self.level}", True, (255, 255, 0))
        self.screen.blit(lvl_text, (hp_x + 120, hp_y - 25))

        # --- ITENS E MUNIÇÃO (CONTAGEM) ---
        items_x = self.W - 350
        
        def draw_stat(icon_tex, val, x_off, color=(255,255,255)):
            icon_s = pygame.transform.scale(icon_tex, (32, 32))
            self.screen.blit(icon_s, (items_x + x_off, self.H - 75))
            txt = self.font.render(str(val), True, color)
            self.screen.blit(txt, (items_x + x_off + 40, self.H - 65))

        draw_stat(self.tex_medkit, self.player.medkits, 0, (100, 255, 100))
        draw_stat(self.tex_grenade, self.player.grenades, 100, (200, 200, 100))
        
        ammo_txt = self.font.render(f"AMMO: {self.player.ammo}", True, (255, 215, 0))
        self.screen.blit(ammo_txt, (self.W - 130, self.H - 65))

        # --- WATERMARK ---
        v_txt = self.font.render("v9.0 SYNC", True, (0, 255, 0))
        self.screen.blit(v_txt, (self.W - 120, 20))
        
        # --- NET DEBUG LOGS ---
        for i, log in enumerate(self.net_debug_logs):
            lt = self.font.render(log, True, (0, 255, 255))
            self.screen.blit(lt, (10, 10 + i * 20))
        
        # --- STATUS INFO ---
        st_txt = self.font.render(f"ID:{self.player_id} | STATE:{self.game_state} | WS:{self.ws}", True, (255, 120, 0))
        self.screen.blit(st_txt, (10, self.H - 60))

        # --- OUTROS AVISOS ---
        if self.player_has_key:
            msg = self.font.render("CHAVE COLETADA! VÁ AO PORTAL", True, (255, 255, 0))
            self.screen.blit(msg, (self.W//2 - msg.get_width()//2, 50))
            
        icon = self.p_icon if self.player.weapon_idx == 0 else self.s_icon
        self.screen.blit(pygame.transform.scale(icon, (64, 64)), (self.W - 80, self.H - 140))

        # (Animação 2D de arremesso removida para evitar poluição visual e imagem dupla)

        if self.wep_msg_timer > 0:
            msg = self.big_font.render("SHOTGUN DESBLOQUEADA!", True, (255, 255, 0))
            self.screen.blit(msg, (self.W//2 - msg.get_width()//2, self.H//2))

        if self.headshot_msg_timer > 0:
            msg = self.big_font.render("HEADSHOT!", True, (255, 0, 0))
            self.screen.blit(msg, (self.W//2 - msg.get_width()//2, self.H//4 + 50))

        if self.hit_marker > 0:
           pygame.draw.circle(self.screen, (255, 255, 255), (int(self.mira_x), int(self.mira_y)), 15, 2)
        else:
           # Mira padrão
           pygame.draw.circle(self.screen, (255, 255, 255), (int(self.mira_x), int(self.mira_y)), 2, 1)
           pygame.draw.line(self.screen, (255, 255, 255), (self.mira_x - 10, self.mira_y), (self.mira_x + 10, self.mira_y), 1)
           pygame.draw.line(self.screen, (255, 255, 255), (self.mira_x, self.mira_y - 10), (self.mira_x, self.mira_y + 10), 1)
           
        # --- INDICADOR DE REDE (DEBUG) ---
        if self.net_packet_received > 0:
            self.net_packet_received -= 0.016 # dt aproximado
            pygame.draw.circle(self.screen, (0, 255, 0), (self.W - 20, 20), 8)
        else:
            pygame.draw.circle(self.screen, (100, 0, 0), (self.W - 20, 20), 8)
            
        if self.player.hp <= 30:
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            ov.fill((120, 0, 0, int(60*(1+math.sin(pygame.time.get_ticks()*0.01)))))
            self.screen.blit(ov, (0, 0))
            
        if self.heal_flash > 0:
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            ov.fill((50, 200, 50, int(50 * self.heal_flash)))
            self.screen.blit(ov, (0, 0))

        pygame.display.flip()

async def main():
    print("--- ASYNC MAIN START ---")
    try:
        game = Game()
        await game.run()
    except Exception as e:
        print("ERROR IN MAIN:", e)
        traceback.print_exc()

if __name__ == "__main__":
    print("--- STARTING EVENT LOOP ---")
    asyncio.run(main())

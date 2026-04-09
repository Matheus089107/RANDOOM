#include "raylib.h"
#include "constants.hpp"
#include <vector>
#include <string>
#include <math.h>
#include <algorithm>

// --- Estruturas de Dados ---
struct Player {
    float x = 1.5f;
    float y = 1.5f;
    float angle = 0.0f;
    int hp = 100;
    int ammo = 50;
};

struct RayResult {
    float distance;
    int mapX, mapY;
    int side; // 0 para X, 1 para Y
};

// --- Funções Auxiliares ---
float wrap_angle(float a) {
    return fmod(a + PI, 2.0f * PI) - PI;
}

// --- Classe do Mundo ---
class World {
public:
    std::vector<std::string> grid;
    int w, h;

    World(std::vector<std::string> g) : grid(g) {
        h = grid.size();
        w = h > 0 ? grid[0].size() : 0;
    }

    bool is_wall(int x, int y) {
        if (x < 0 || x >= w || y < 0 || y >= h) return true;
        return grid[y][x] != '.';
    }

    RayResult cast_ray(float ox, float oy, float ang) {
        float dx = cos(ang);
        float dy = sin(ang);

        int mapX = (int)ox;
        int mapY = (int)oy;

        float deltaDistX = std::abs(1.0f / dx);
        float deltaDistY = std::abs(1.0f / dy);

        int stepX, stepY;
        float sideDistX, sideDistY;

        if (dx < 0) {
            stepX = -1;
            sideDistX = (ox - mapX) * deltaDistX;
        } else {
            stepX = 1;
            sideDistX = (mapX + 1.0f - ox) * deltaDistX;
        }

        if (dy < 0) {
            stepY = -1;
            sideDistY = (oy - mapY) * deltaDistY;
        } else {
            stepY = 1;
            sideDistY = (mapY + 1.0f - oy) * deltaDistY;
        }

        int side = 0;
        float perpDist = 0;

        for (int i = 0; i < 100; i++) {
            if (sideDistX < sideDistY) {
                sideDistX += deltaDistX;
                mapX += stepX;
                side = 0;
            } else {
                sideDistY += deltaDistY;
                mapY += stepY;
                side = 1;
            }

            if (is_wall(mapX, mapY)) break;
        }

        if (side == 0) perpDist = (mapX - ox + (1 - stepX) / 2.0f) / dx;
        else          perpDist = (mapY - oy + (1 - stepY) / 2.0f) / dy;

        return {perpDist, mapX, mapY, side};
    }
};

// --- Loop Principal ---
int main() {
    InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "Ultimate Doom C++ (Raylib)");
    SetTargetFPS(60);

    World world(map_0);
    Player player;

    while (!WindowShouldClose()) {
        float dt = GetFrameTime();

        // --- Inputs ---
        if (IsKeyDown(KEY_W)) {
            float nx = player.x + cos(player.angle) * 3.0f * dt;
            float ny = player.y + sin(player.angle) * 3.0f * dt;
            if (!world.is_wall((int)nx, (int)player.y)) player.x = nx;
            if (!world.is_wall((int)player.x, (int)ny)) player.y = ny;
        }
        if (IsKeyDown(KEY_S)) {
            float nx = player.x - cos(player.angle) * 3.0f * dt;
            float ny = player.y - sin(player.angle) * 3.0f * dt;
            if (!world.is_wall((int)nx, (int)player.y)) player.x = nx;
            if (!world.is_wall((int)player.x, (int)ny)) player.y = ny;
        }
        if (IsKeyDown(KEY_A)) player.angle -= 2.5f * dt;
        if (IsKeyDown(KEY_D)) player.angle += 2.5f * dt;

        // --- Renderização ---
        BeginDrawing();
            ClearBackground(BLACK);

            // Chão e Teto
            DrawRectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT / 2, DARKGRAY);
            DrawRectangle(0, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT / 2, DARKGREEN);

            // Raycasting Loop
            int num_rays = SCREEN_WIDTH / RENDER_SCALE;
            for (int i = 0; i < num_rays; i++) {
                float camX = 2.0f * i / (float)num_rays - 1.0f;
                float rayAng = player.angle + atan(camX * tan(FOV / 2.0f));
                
                RayResult res = world.cast_ray(player.x, player.y, rayAng);
                float dist = res.distance * cos(rayAng - player.angle);

                int wallHeight = (int)(SCREEN_HEIGHT / std::max(0.0001f, dist));
                int y0 = (SCREEN_HEIGHT - wallHeight) / 2;

                Color wallColor = (res.side == 1) ? Color{150, 70, 70, 255} : Color{200, 100, 100, 255};
                
                DrawRectangle(i * RENDER_SCALE, y0, RENDER_SCALE, wallHeight, wallColor);
            }

            // HUD Simples
            DrawText(TextFormat("FPS: %i", GetFPS()), 10, 10, 20, YELLOW);
            DrawText(TextFormat("POS: %.2f, %.2f", player.x, player.y), 10, 40, 20, GREEN);
            
        EndDrawing();
    }

    CloseWindow();
    return 0;
}

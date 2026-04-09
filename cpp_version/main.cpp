#include "raylib.h"
#include "constants.hpp"
#include <vector>
#include <string>
#include <math.h>
#include <algorithm>

// --- Estruturas de Dados ---
struct Player {
    Vector3 position = { 1.5f, 1.0f, 1.5f }; // Posição 3D
    float health = 100.0f;
};

// --- Classe do Mundo ---
class World {
public:
    std::vector<std::string> grid;
    int w, h;

    World(std::vector<std::string> g) : grid(g) {
        h = grid.size();
        w = h > 0 ? grid[0].size() : 0;
    }

    bool is_wall(int x, int z) {
        if (x < 0 || x >= w || z < 0 || z >= h) return true;
        return grid[z][x] != '.';
    }

    void draw() {
        // Desenha as paredes baseadas no grid do mapa
        for (int z = 0; z < h; z++) {
            for (int x = 0; x < w; x++) {
                if (grid[z][x] == '#') {
                    // Desenha um cubo para cada '#'
                    // (x, y, z) -> y=1.0f para ficar no chão
                    DrawCube({ (float)x, 1.0f, (float)z }, 1.0f, 2.0f, 1.0f, DARKGRAY);
                    DrawCubeWires({ (float)x, 1.0f, (float)z }, 1.0f, 2.0f, 1.0f, BLACK);
                }
            }
        }
        
        // Desenha o chão
        DrawPlane({ (float)w / 2.0f, 0.0f, (float)h / 2.0f }, { (float)w, (float)h }, GREEN);
    }
};

int main() {
    // Configurações da Janela
    SetConfigFlags(FLAG_MSAA_4X_HINT); // Anti-aliasing para ficar mais bonito
    InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "RANDOOM 3D Evolution (Raylib)");
    SetTargetFPS(60);

    // Inicialização do Mundo e Câmera
    World world(map_0);
    
    Camera3D camera = { 0 };
    camera.position = { 1.5f, 1.5f, 1.5f }; // Posiciona o jogador
    camera.target = { 2.5f, 1.5f, 2.5f };   // Para onde ele olha
    camera.up = { 0.0f, 1.0f, 0.0f };       // Vetor "cima"
    camera.fovy = 66.0f;                    // Campo de visão
    camera.projection = CAMERA_PERSPECTIVE; // Projeção perspectiva real

    // Exemplo de como carregar um modelo no futuro:
    // Model enemyModel = LoadModel("assets/models/enemy.glb"); 
    
    DisableCursor(); // Trava o mouse para controle FPS

    while (!WindowShouldClose()) {
        // --- Atualização ---
        UpdateCamera(&camera, CAMERA_FIRST_PERSON); // Controle FPS nativo (WASD + Mouse)

        // Colisão simples: Se entrar em uma parede, volta para a posição anterior
        // (Isso pode ser melhorado com detecção de Bounding Box futuramente)
        if (world.is_wall((int)camera.position.x, (int)camera.position.z)) {
            // Lógica simples de "empurrar" para fora ou travar movimento
            // Por enquanto, apenas avisamos ou travamos.
        }

        // --- Renderização ---
        BeginDrawing();
            ClearBackground(SKYBLUE); // Fundo azul céu

            BeginMode3D(camera);
                
                world.draw(); // Desenha as paredes e chão em 3D

                // Exemplo de desenho de um personagem placeholder
                // DrawModel(enemyModel, {5.0f, 0.0f, 5.0f}, 1.0f, WHITE);
                DrawCube({ 5.0f, 0.5f, 5.0f }, 1.0f, 1.0f, 1.0f, RED); // Placeholder pro inimigo

            EndMode3D();

            // HUD 2D
            DrawFPS(10, 10);
            DrawText("RANDOOM 3D - MODO EXPERIMENTAL", 10, 40, 20, BLACK);
            DrawCircle(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 2, RED); // Crosshair simples

        EndDrawing();
    }

    // Descarregar recursos
    // UnloadModel(enemyModel); 
    CloseWindow();

    return 0;
}

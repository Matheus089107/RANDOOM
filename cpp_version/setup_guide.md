# 🛠️ Guia de Transição: Python -> C++ (Raylib 3D)

O seu motor agora é um **Motor 3D Real**. Em vez de apenas simular profundidade, estamos usando o pipeline 3D completo da Raylib.

## 1. Instalando o Compilador (Windows)

Como você está no Windows, recomendo usar o **MinGW-w64** ou o **Visual Studio**.

### Opção A: Visual Studio (Recomendado)
1.  Baixe o [Visual Studio Community 2022](https://visualstudio.microsoft.com/vs/community/).
2.  Durante a instalação, marque a opção **"Desenvolvimento para desktop com C++"**.
3.  Isso instalará o compilador `cl.exe` e as ferramentas necessárias.

### Opção B: MinGW (Leve)
1.  Baixe o [w64devkit](https://github.com/skeeto/w64devkit/releases) (é um arquivo .zip com tudo pronto).
2.  Extraia em uma pasta (ex: `C:\w64devkit`).
3.  Adicione a pasta `bin` ao seu PATH do Windows.

## 2. Instalando a Raylib

A Raylib é a biblioteca que substitui o Pygame.
1.  Vá em [raylib.com](https://www.raylib.com/) e baixe a versão para o seu compilador.
2.  Coloque os arquivos `.h` e `.lib` na pasta do projeto.

## 3. O que mudou no código? (Evolução 3D)

| Recurso | Antigo (Raycaster) | Novo (Motor 3D Real) |
| :--- | :--- | :--- |
| **Câmera** | Manual (Lógica de raios) | `Camera3D` do Raylib (Perspectiva real) |
| **Personagens** | Sprites 2D (Billboarding) | **Modelos 3D (.obj, .glb)** |
| **Mundo** | Retângulos 2D | Cubos e Meshes 3D (`DrawCube`) |
| **Mouse** | Travado no centro | Controle FPS real (Mouse livre no 3D) |

## 4. Como usar seus Modelos do Blender

1.  Exporte seu personagem no Blender como **.glb** ou **.gltf**.
2.  Coloque o arquivo na pasta: `cpp_version/assets/models/`.
3.  No código `main.cpp`, você já tem o local preparado para usar as funções `LoadModel` e `DrawModel`.

---
**O próximo passo agora é importar seu primeiro modelo do Blender!**

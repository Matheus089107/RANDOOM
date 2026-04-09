# 🛠️ Guia de Transição: Python -> C++ (Raylib)

Você decidiu subir de nível! C++ é a linguagem dos deuses do desenvolvimento de jogos, e a **Raylib** é a ferramenta perfeita para essa missão. Abaixo está o que você precisa para rodar o código que eu acabei de criar.

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
1.  Vá em [raylib.com](https://www.raylib.com/) e baixe a versão para o seu compilador (MSVC para Visual Studio ou MinGW).
2.  Coloque os arquivos `.h` e `.lib` na pasta do projeto `Doom_CPP`.

## 3. O que mudou no código?

| Recurso | Python (Pygame) | C++ (Raylib) |
| :--- | :--- | :--- |
| **Loop Principal** | `while True` + `asyncio` | `while (!WindowShouldClose())` |
| **Desenho** | `screen.blit()` | `DrawTexture()` ou `DrawRectangle()` |
| **Matemática** | `math.cos()`, `math.sin()` | `cos()`, `sin()` (mais rápido nativamente) |
| **Tipagem** | Dinâmica (v: float) | Estática (`float x`) - evita muitos bugs! |

## 4. Próximos Passos

Eu já criei a base do seu motor em C++ na pasta `Doom_CPP`. 
Para portar o **Multijogador**, precisaremos de uma biblioteca de rede adicional (como `IXWebSocket` ou `ASIO`), já que o C++ não tem WebSockets nativos como o Python.

> [!TIP]
> O desempenho que você verá ao rodar esse código em C++ será absurdo. Você poderá renderizar milhares de raios e texturas sem quedas de FPS.

**Você gostaria que eu continuasse portando o sistema de Inimigos e Inteligência Artificial agora?**

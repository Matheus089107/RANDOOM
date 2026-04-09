# 💀 RANDOOM

Bem-vindo ao **RANDOOM**, um projeto de tiro em primeira pessoa inspirado no clássico Doom, desenvolvido como um motor de jogo 2.5D completo.

🚀 **Jogue agora no navegador:** [https://doom-pygame-25d.vercel.app/](https://doom-pygame-25d.vercel.app/)

---

## 👥 Desenvolvedores

-   **Matheus**: Idealização, lógica do motor, renderização e gráficos.
-   **Eduardo**: Direção de arte, criação de personagens, imagens e assets visuais.

---

## 🎮 Mecânicas do Jogo

O **RANDOOM** oferece uma progressão de níveis desafiadora com as seguintes mecânicas:

-   **Progressão por Portal**: Para avançar de nível, você deve encontrar o portal. Ele só será ativado após você coletar a **chave**.
-   **O Sistema de Chave**: Em cada nível, o **último inimigo vivo** (ou o chefe) deixará cair a chave do portal ao morrer. Fique atento ao local da última baixa!
-   **Arsenal Progressivo**:
    -   Você inicia sua jornada apenas com a **Pistola**.
    -   A **Escopeta** é desbloqueada automaticamente ao atingir o **Nível 4**.
-   **Itens**: Procure por kits médicos (+30 HP) e granadas espalhados pelo mapa para sobreviver às hordas.

### 🌐 Modo Online (Multijogador)
> [!IMPORTANT]
> O modo online ainda está em fase de ajuste. Existe uma chance de funcionar, mas instabilidades podem ocorrer. Estamos trabalhando para estabilizar a conexão entre os jogadores!

---

## 🕹️ Como Jogar (Controles)

| Tecla | Ação |
| :--- | :--- |
| **W, A, S, D** | Movimentação (Frente, Esquerda, Trás, Direita) |
| **Mouse** | Olhar ao redor / Mirar |
| **Clique Esquerdo** | Atirar |
| **Espaço** | Lançar Granada |
| **TAB** | Usar Kit Médico |
| **Shift** | Correr |
| **1 / 2** | Trocar de Arma (Pistola / Escopeta - Nível 4+) |
| **M** | Travar/Destravar o Mouse (Útil para a versão web) |
| **ESC** | Abrir Menu / Sair |

---

## 📂 Estrutura do Repositório

-   `main.py`: Versão original em **Python** (2.5D Raycaster com Multijogador).
-   `cpp_version/`: Nova versão em **C++** de alta performance usando **Raylib**.
-   `images/`: Assets visuais (texturas, sprites, animações).
-   `server.py`: Servidor de relay para o modo multijogador.

## 🚀 Execução Local (Python)

Certifique-se de ter o Pygame instalado:
```bash
pip install pygame
python main.py
```

---
Desenvolvido com foco em performance e estética premium por Matheus & Eduardo.

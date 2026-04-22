#!/bin/bash
set -e

# Instalar dependências
pip install -r requirements.txt

# Remover builds antigos
rm -rf build
rm -rf temp_game

# Criar pasta temporária contendo APENAS o jogo (evita empacotar .venv)
mkdir temp_game
cp main.py temp_game/
cp -r images temp_game/

# Gerar o site estático do jogo com Pygbag
python -m pygbag --build temp_game

# Mover o build para o local onde o server.py espera encontrar
mkdir -p build
mv temp_game/build/web build/web

# Limpar
rm -rf temp_game

# Corrigir o bug do BrowserFS do Pygbag no index.html final
sed -i 's|https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js|https://cdnjs.cloudflare.com/ajax/libs/BrowserFS/2.0.0/browserfs.min.js|g' build/web/index.html

echo "Build concluído com sucesso!"

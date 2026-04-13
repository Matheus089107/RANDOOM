#!/bin/bash
set -e

# Instalar dependências
pip install -r requirements.txt

# Gerar o site estático do jogo com Pygbag
python -m pygbag --build .

# Corrigir o bug do BrowserFS do Pygbag no index.html final
sed -i 's|https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js|https://cdnjs.cloudflare.com/ajax/libs/BrowserFS/2.0.0/browserfs.min.js|g' build/web/index.html

echo "Build concluído com sucesso!"

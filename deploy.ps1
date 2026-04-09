$env:PYTHONUTF8="1"
echo "Gerando versão Web do jogo usando Pygbag..."
python -m pygbag --build .
if ($LASTEXITCODE -ne 0) {
    echo "Erro ao gerar build do Pygbag!"
    exit $LASTEXITCODE
}

echo "Corrigindo bug do Pygbag (link quebrado do BrowserFS)..."
(Get-Content build\web\index.html) -replace "https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js", "https://cdnjs.cloudflare.com/ajax/libs/BrowserFS/2.0.0/browserfs.min.js" | Set-Content build\web\index.html

echo "Fazendo upload para o Vercel em produção..."
cd build/web
npx vercel --prod
if ($LASTEXITCODE -ne 0) {
    echo "Erro ao fazer o deploy no Vercel!"
    exit $LASTEXITCODE
}

echo "Pronto! O jogo foi atualizado online."

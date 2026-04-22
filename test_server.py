import asyncio
import websockets
import json

async def test_room():
    uri = "wss://doom-multiplayer.onrender.com/ws"
    room = "9999"
    
    print(f"Conectando ao servidor: {uri}")
    try:
        async with websockets.connect(uri) as ws1:
            # Jogador 1 entra
            await ws1.send(json.dumps({"type": "join", "room": room, "id": "TEST_1"}))
            print("Jogador 1 enviou JOIN")
            
            async with websockets.connect(uri) as ws2:
                # Jogador 2 entra
                await ws2.send(json.dumps({"type": "join", "room": room, "id": "TEST_2"}))
                print("Jogador 2 enviou JOIN")
                
                # Jogador 1 deve receber aviso de que Jogador 2 chegou
                # Usamos um timeout curto
                try:
                    msg1 = await asyncio.wait_for(ws1.recv(), timeout=5.0)
                    print(f"Jogador 1 recebeu: {msg1}")
                except asyncio.TimeoutError:
                    print("TIMEOUT: Jogador 1 não recebeu nada")
                    return
                
                # Jogador 2 deve receber aviso de que Jogador 1 já estava lá
                try:
                    msg2 = await asyncio.wait_for(ws2.recv(), timeout=5.0)
                    print(f"Jogador 2 recebeu: {msg2}")
                except asyncio.TimeoutError:
                    print("TIMEOUT: Jogador 2 não recebeu nada")
                    return
                
                if "TEST_2" in msg1 and "TEST_1" in msg2:
                    print("SUCCESS: Sincronização do servidor está funcionando!")
                else:
                    print("FAILURE: Servidor não sincronizou os IDs corretamente.")
                    
    except Exception as e:
        print(f"ERROR: Não foi possível testar o servidor: {e}")

if __name__ == "__main__":
    asyncio.run(test_room())

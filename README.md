# ◈ PrimeSense Carmine — Painel de Controle

Interface gráfica (GUI) em **CustomTkinter** para visualização em tempo real dos streams de uma câmera de profundidade **PrimeSense Carmine 1.09 (Short Range)** através do **OpenNI2**.

Permite alternar entre os sensores de profundidade, infravermelho e cor, exibir múltiplos streams simultaneamente em grade, aplicar colormaps na imagem de profundidade e realçar a qualidade visual dos frames.

---

## Funcionalidades

- **Modos single:** Profundidade (Depth), Infravermelho (IR) e Cor (RGB).
- **Modos multi:**
  - **Dual** — Depth + IR lado a lado.
  - **Trial** — Depth + IR + Color em grade (2 em cima, 1 centralizado embaixo).
- **Colormaps de profundidade:** JET, TURBO, PLASMA, INFERNO e HOT, selecionáveis em tempo real.
- **Realce de imagem** (toggle "Melhorar qualidade"): filtro bilateral, equalização adaptativa de contraste (CLAHE) e *unsharp mask*.
- **Tratamento do stream de profundidade:** normalização para 8 bits, *inpainting* (TELEA) para preencher buracos de leitura (pixels = 0) e suavização bilateral.
- **Labels** sobrepostos em cada frame nos modos multi e indicador de status do dispositivo na sidebar.
- Encerramento limpo dos streams e do OpenNI2 ao fechar a janela.

---

## Requisitos

### Hardware
- Câmera **PrimeSense Carmine 1.09 / Xtion** (ou compatível com OpenNI2).
- Porta USB 2.0 ou superior.

### Software
- **Linux** (o código aponta para `/usr/lib/x86_64-linux-gnu`; em outros sistemas é necessário ajustar o caminho do OpenNI2).
- **Python 3.8+**.
- Runtime do **OpenNI2** instalado no sistema (bibliotecas `.so`), além do pacote Python `primesense`.

---

## Instalação

### 1. Runtime do OpenNI2 (nível de sistema)

O pacote Python `primesense` é apenas um *wrapper* — ele precisa das bibliotecas nativas do OpenNI2 instaladas.

**Debian / Ubuntu:**
```bash
sudo apt update
sudo apt install libopenni2-0 libopenni2-dev
```

Verifique onde as bibliotecas foram instaladas (o código espera `/usr/lib/x86_64-linux-gnu`):
```bash
find / -name "libOpenNI2.so" 2>/dev/null
```

> Caso o caminho seja diferente, ajuste a chamada `openni2.initialize("...")` no método `inicializar_sensor`.

### 2. Dependências Python

Recomenda-se usar um ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Como usar

```bash
python3 main.py
```
*(substitua `main.py` pelo nome do arquivo onde está o código)*

Ao iniciar, a aplicação abre no modo **Profundidade**. Use a sidebar para alternar entre os modos e ajustar as opções.

### Controles

| Botão / Controle        | Ação                                                |
|-------------------------|-----------------------------------------------------|
| **Profundidade**        | Stream de depth com colormap.                       |
| **Infravermelho**       | Stream IR em escala de cinza (convertida p/ BGR).   |
| **Cor (RGB)**           | Stream de cor.                                      |
| **Dual (Depth + IR)**   | Depth e IR simultâneos lado a lado.                 |
| **Trial (todos)**       | Depth, IR e Color simultâneos em grade.             |
| **Colormap depth**      | Troca o mapa de cores aplicado à profundidade.      |
| **Melhorar qualidade**  | Liga/desliga o realce de imagem.                    |
| **Sair**                | Encerra streams, descarrega o OpenNI2 e fecha.      |

---

## Estrutura do código

A aplicação é composta por uma única classe `XtionAppGUI` (herda de `ctk.CTk`), organizada em blocos:

- **Build UI** — `_build_sidebar`, `_build_video_area`: construção da interface.
- **Sensor** — `inicializar_sensor`: inicializa o OpenNI2 e cria os streams.
- **Controles** — `mudar_modo`, `atualizar_botoes`, `_parar_todos`, `_on_cmap_change`.
- **Processamento** — `ler_depth`, `ler_ir`, `ler_color`, `melhorar`, `adicionar_label`, `montar_grid`.
- **Loop de vídeo** — `atualizar_video`: agendado via `after(16, ...)` (~60 FPS alvo).
- **Cleanup** — `ao_fechar`: encerramento seguro.

---

## Solução de problemas

- **`Falha ao iniciar sensor` / erro no `initialize`:** confirme que o runtime do OpenNI2 está instalado e que o caminho passado para `openni2.initialize(...)` está correto.
- **Câmera não detectada:** verifique a conexão USB e as permissões do dispositivo (pode ser necessário configurar regras *udev* ou rodar com privilégios adequados).
- **`ImportError: primesense`:** instale as dependências com `pip install -r requirements.txt` dentro do ambiente virtual ativo.
- **Conflito entre streams:** o modo Dual evita o stream de cor de propósito, pois alguns dispositivos não suportam Depth + IR + Color simultaneamente. Se o modo Trial falhar, prefira Dual.

---

## Observações

- Os caminhos de biblioteca e o nome do dispositivo são específicos para Linux x86_64; portabilidade para Windows/macOS exige ajustar a inicialização do OpenNI2.
- O loop de atualização usa `after(16, ...)`; em hardware mais limitado, aumentar esse intervalo reduz o uso de CPU.

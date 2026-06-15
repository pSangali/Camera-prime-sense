import cv2
import numpy as np
import sys
from primesense import openni2
from primesense import _openni2 as c_api
import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class XtionAppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PrimeSense Carmine — Painel de Controle")
        self.geometry("1100x650")
        self.minsize(900, 550)
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)

        self.dev          = None
        self.ir_stream    = None
        self.depth_stream = None
        self.color_stream = None
        self.modo_atual   = "DEPTH"
        self.loop_id      = None
        self.colormap_idx = 0
        self.enhance      = True

        # Cache de frames para os modos multi
        self._frame_depth = None
        self._frame_ir    = None
        self._frame_color = None

        self.COLORMAPS = [
            ("JET",     cv2.COLORMAP_JET),
            ("TURBO",   cv2.COLORMAP_TURBO),
            ("PLASMA",  cv2.COLORMAP_PLASMA),
            ("INFERNO", cv2.COLORMAP_INFERNO),
            ("HOT",     cv2.COLORMAP_HOT),
        ]

        # Modos simples vs multi
        self.MODOS_SIMPLES = ("DEPTH", "IR", "COLOR")
        self.MODOS_MULTI   = ("DUAL", "TRIAL")

        if not self.inicializar_sensor():
            print("Falha ao iniciar sensor")
            sys.exit(1)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_video_area()

        self.depth_stream.start()
        self.atualizar_botoes()
        self.atualizar_video()

    # ─── Build UI ─────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(self.sidebar, text="◈ PrimeSense",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#00f5c4").grid(row=0, column=0, padx=20, pady=(20, 2))

        ctk.CTkLabel(self.sidebar, text="Carmine 1.09 Short Range",
                     font=ctk.CTkFont(size=10),
                     text_color="#44445a").grid(row=1, column=0, padx=20, pady=(0, 10))

        # Separador — streams simples
        ctk.CTkLabel(self.sidebar, text="SINGLE",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#44445a").grid(row=2, column=0, padx=20, pady=(6, 2), sticky="w")

        self.btn_depth = ctk.CTkButton(self.sidebar, text="⬤  Profundidade",
                                        command=lambda: self.mudar_modo("DEPTH"))
        self.btn_depth.grid(row=3, column=0, padx=20, pady=3)

        self.btn_ir = ctk.CTkButton(self.sidebar, text="⬤  Infravermelho",
                                     command=lambda: self.mudar_modo("IR"))
        self.btn_ir.grid(row=4, column=0, padx=20, pady=3)

        self.btn_color = ctk.CTkButton(self.sidebar, text="⬤  Cor (RGB)",
                                        command=lambda: self.mudar_modo("COLOR"))
        self.btn_color.grid(row=5, column=0, padx=20, pady=3)

        # Separador — multi
        ctk.CTkLabel(self.sidebar, text="MULTI",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#44445a").grid(row=6, column=0, padx=20, pady=(10, 2), sticky="w")

        self.btn_dual = ctk.CTkButton(self.sidebar, text="⊟  Dual  (Depth + IR)",
                                       command=lambda: self.mudar_modo("DUAL"))
        self.btn_dual.grid(row=7, column=0, padx=20, pady=3)

        self.btn_trial = ctk.CTkButton(self.sidebar, text="⊞  Trial  (todos)",
                                        command=lambda: self.mudar_modo("TRIAL"))
        self.btn_trial.grid(row=8, column=0, padx=20, pady=3)

        # Colormap
        self.lbl_cmap = ctk.CTkLabel(self.sidebar, text="Colormap depth:",
                                      font=ctk.CTkFont(size=11), text_color="#888")
        self.cmap_var = ctk.StringVar(value="JET")
        self.cmap_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=[c[0] for c in self.COLORMAPS],
            variable=self.cmap_var,
            command=self._on_cmap_change,
            width=180
        )
        self.lbl_cmap.grid(row=9, column=0, padx=20, pady=(10, 2))
        self.cmap_menu.grid(row=10, column=0, padx=20, pady=(0, 4))

        # Enhance toggle
        self.enhance_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.sidebar, text="Melhorar qualidade",
                        variable=self.enhance_var,
                        command=lambda: setattr(self, 'enhance', self.enhance_var.get()),
                        font=ctk.CTkFont(size=11)).grid(row=11, column=0, padx=20, pady=6)

        # Status
        try:
            info = self.dev.get_device_info()
            nome = info.name.decode() if isinstance(info.name, bytes) else str(info.name)
        except:
            nome = "Dispositivo OK"

        ctk.CTkLabel(self.sidebar, text=f"● Online\n{nome}",
                     font=ctk.CTkFont(size=10),
                     text_color="#00f5c4", justify="center").grid(row=12, column=0, padx=20, pady=8)

        ctk.CTkButton(self.sidebar, text="✕  Sair",
                      fg_color="#7a1f1f", hover_color="#a03030",
                      command=self.ao_fechar).grid(row=13, column=0, padx=20, pady=(4, 20))

    def _build_video_area(self):
        self.video_container = ctk.CTkFrame(self, corner_radius=10)
        self.video_container.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
        self.video_container.grid_rowconfigure(0, weight=1)
        self.video_container.grid_columnconfigure(0, weight=1)

        self.lbl_video = ctk.CTkLabel(self.video_container,
                                       text="Inicializando câmera...",
                                       font=ctk.CTkFont(size=14))
        self.lbl_video.grid(row=0, column=0, sticky="nsew")

        self.lbl_info = ctk.CTkLabel(self.video_container,
                                      text="OpenNI2 · PrimeSense",
                                      font=ctk.CTkFont(size=10),
                                      text_color="#44445a")
        self.lbl_info.grid(row=1, column=0, pady=(0, 6))

    # ─── Sensor ───────────────────────────────────────────────

    def inicializar_sensor(self):
        try:
            openni2.initialize("/usr/lib/x86_64-linux-gnu")
            self.dev          = openni2.Device.open_any()
            self.depth_stream = self.dev.create_depth_stream()
            self.ir_stream    = self.dev.create_ir_stream()
            self.color_stream = self.dev.create_color_stream()
            return True
        except Exception as e:
            print("Erro ao inicializar sensor:", e)
            return False

    # ─── Controles ────────────────────────────────────────────

    def _on_cmap_change(self, value):
        for i, (name, _) in enumerate(self.COLORMAPS):
            if name == value:
                self.colormap_idx = i

    def _parar_todos(self):
        for s in [self.ir_stream, self.depth_stream, self.color_stream]:
            try:
                s.stop()
            except:
                pass

    def atualizar_botoes(self):
        ON, OFF = "#1f538d", "#2b2b2b"
        m = self.modo_atual
        self.btn_depth.configure(fg_color=ON if m == "DEPTH" else OFF)
        self.btn_ir.configure(   fg_color=ON if m == "IR"    else OFF)
        self.btn_color.configure(fg_color=ON if m == "COLOR" else OFF)
        self.btn_dual.configure( fg_color=ON if m == "DUAL"  else OFF)
        self.btn_trial.configure(fg_color=ON if m == "TRIAL" else OFF)

    def mudar_modo(self, novo_modo):
        if novo_modo == self.modo_atual:
            return
        self._parar_todos()
        try:
            if novo_modo == "DEPTH":
                self.depth_stream.start()
            elif novo_modo == "IR":
                self.ir_stream.start()
            elif novo_modo == "COLOR":
                self.color_stream.start()
            elif novo_modo == "DUAL":
                # Depth + IR (sem color — evita conflito)
                self.depth_stream.start()
                self.ir_stream.start()
            elif novo_modo == "TRIAL":
                # Depth + IR + Color
                self.depth_stream.start()
                self.ir_stream.start()
                self.color_stream.start()

            self.modo_atual = novo_modo
            self.atualizar_botoes()
        except Exception as e:
            print("Erro ao trocar modo:", e)

    # ─── Processamento ────────────────────────────────────────

    def melhorar(self, frame_bgr):
        if not self.enhance:
            return frame_bgr
        f    = cv2.bilateralFilter(frame_bgr, 5, 35, 35)
        lab  = cv2.cvtColor(f, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        f    = cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2BGR)
        blur = cv2.GaussianBlur(f, (0, 0), 1.2)
        return cv2.addWeighted(f, 1.35, blur, -0.35, 0)

    def ler_depth(self):
        frame = self.depth_stream.read_frame()
        img   = np.frombuffer(frame.get_buffer_as_uint16(),
                              dtype=np.uint16).reshape(frame.height, frame.width)
        mask  = (img == 0).astype(np.uint8)
        img8  = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        img8  = cv2.inpaint(img8, mask, 3, cv2.INPAINT_TELEA)
        if self.enhance:
            img8 = cv2.bilateralFilter(img8, 7, 50, 50)
        return cv2.applyColorMap(img8, self.COLORMAPS[self.colormap_idx][1])

    def ler_ir(self):
        frame = self.ir_stream.read_frame()
        img   = np.frombuffer(frame.get_buffer_as_uint16(),
                              dtype=np.uint16).reshape(frame.height, frame.width)
        img8  = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        bgr   = cv2.cvtColor(img8, cv2.COLOR_GRAY2BGR)
        return self.melhorar(bgr)

    def ler_color(self):
        frame = self.color_stream.read_frame()
        img   = np.frombuffer(frame.get_buffer_as_uint8(),
                              dtype=np.uint8).reshape(frame.height, frame.width, 3)
        bgr   = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return self.melhorar(bgr)

    def adicionar_label(self, img, texto, cor=(255, 255, 255)):
        """Escreve um label no canto superior esquerdo do frame."""
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (len(texto) * 9 + 10, 24), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)
        cv2.putText(img, texto, (6, 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor, 1, cv2.LINE_AA)
        return img

    def montar_grid(self, frames_labels):
        """
        Monta grade de frames com labels.
        frames_labels: lista de (frame_bgr, 'LABEL', cor)
        2 frames → lado a lado
        3 frames → 2 em cima, 1 centralizado embaixo
        """
        w = self.video_container.winfo_width() - 20
        h = self.video_container.winfo_height() - 40

        n = len(frames_labels)

        if n == 2:
            fw, fh = w // 2, h
            resized = []
            for frame, label, cor in frames_labels:
                f = cv2.resize(frame, (fw - 4, fh - 4), interpolation=cv2.INTER_LANCZOS4)
                f = self.adicionar_label(f, label, cor)
                resized.append(f)
            linha = np.hstack(resized)
            # Padding para bater exato
            if linha.shape[1] < w:
                pad = np.zeros((linha.shape[0], w - linha.shape[1], 3), dtype=np.uint8)
                linha = np.hstack([linha, pad])
            resultado = linha

        else:  # 3 frames — trial
            fw_top = w // 2
            fh_top = h * 2 // 3
            fw_bot = w // 2
            fh_bot = h - fh_top

            f0 = cv2.resize(frames_labels[0][0], (fw_top - 4, fh_top - 4), interpolation=cv2.INTER_LANCZOS4)
            f1 = cv2.resize(frames_labels[1][0], (fw_top - 4, fh_top - 4), interpolation=cv2.INTER_LANCZOS4)
            f2 = cv2.resize(frames_labels[2][0], (fw_bot - 4, fh_bot - 4), interpolation=cv2.INTER_LANCZOS4)

            f0 = self.adicionar_label(f0, frames_labels[0][1], frames_labels[0][2])
            f1 = self.adicionar_label(f1, frames_labels[1][1], frames_labels[1][2])
            f2 = self.adicionar_label(f2, frames_labels[2][1], frames_labels[2][2])

            topo  = np.hstack([f0, np.zeros((fh_top - 4, 4, 3), dtype=np.uint8), f1])
            # Centraliza f2
            pad_l = (topo.shape[1] - f2.shape[1]) // 2
            pad_r = topo.shape[1] - f2.shape[1] - pad_l
            base  = np.hstack([
                np.zeros((f2.shape[0], pad_l, 3), dtype=np.uint8),
                f2,
                np.zeros((f2.shape[0], pad_r, 3), dtype=np.uint8)
            ])
            div   = np.zeros((4, topo.shape[1], 3), dtype=np.uint8)
            resultado = np.vstack([topo, div, base])

        return resultado

    # ─── Loop de vídeo ────────────────────────────────────────

    def atualizar_video(self):
        try:
            modo = self.modo_atual
            w_cont = self.video_container.winfo_width() - 20
            h_cont = self.video_container.winfo_height() - 40

            if modo == "DEPTH":
                frame_bgr = self.ler_depth()
                frame_bgr = cv2.resize(frame_bgr, (w_cont, h_cont), interpolation=cv2.INTER_LANCZOS4) if w_cont > 100 else frame_bgr
                info = "Profundidade"

            elif modo == "IR":
                frame_bgr = self.ler_ir()
                frame_bgr = cv2.resize(frame_bgr, (w_cont, h_cont), interpolation=cv2.INTER_LANCZOS4) if w_cont > 100 else frame_bgr
                info = "Infravermelho"

            elif modo == "COLOR":
                frame_bgr = self.ler_color()
                frame_bgr = cv2.resize(frame_bgr, (w_cont, h_cont), interpolation=cv2.INTER_LANCZOS4) if w_cont > 100 else frame_bgr
                info = "Cor RGB"

            elif modo == "DUAL":
                fd = self.ler_depth()
                fi = self.ler_ir()
                frame_bgr = self.montar_grid([
                    (fd, "DEPTH", (0, 200, 255)),
                    (fi, "IR",    (200, 200, 200)),
                ])
                info = "Dual: Depth + IR"

            elif modo == "TRIAL":
                fd = self.ler_depth()
                fi = self.ler_ir()
                fc = self.ler_color()
                frame_bgr = self.montar_grid([
                    (fd, "DEPTH", (0, 200, 255)),
                    (fi, "IR",    (200, 200, 200)),
                    (fc, "COLOR", (100, 255, 150)),
                ])
                info = "Trial: Depth + IR + Color"

            else:
                self.loop_id = self.after(16, self.atualizar_video)
                return

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            img_tk    = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
            self.lbl_video.configure(image=img_tk, text="")
            self.lbl_video.image = img_tk
            self.lbl_info.configure(
                text=f"{info} · enhance={'ON' if self.enhance else 'OFF'} · OpenNI2"
            )

        except Exception as e:
            print("Erro no vídeo:", e)

        self.loop_id = self.after(16, self.atualizar_video)

    # ─── Cleanup ──────────────────────────────────────────────

    def ao_fechar(self):
        if self.loop_id:
            self.after_cancel(self.loop_id)
        self._parar_todos()
        try:
            openni2.unload()
        except:
            pass
        self.destroy()


if __name__ == "__main__":
    app = XtionAppGUI()
    app.mainloop()
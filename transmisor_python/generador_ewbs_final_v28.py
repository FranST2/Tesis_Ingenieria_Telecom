import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import struct
import sys
import threading

# =========================================================================
#  LÓGICA CORE (INTACTA V26)
# =========================================================================

try:
    from reedsolo import RSCodec
    HAS_REEDSOLO = True
except ImportError:
    HAS_REEDSOLO = False

def calc_crc32_mpeg(data):
    crc = 0xFFFFFFFF; poly = 0x04C11DB7
    for byte in data:
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1; c = (crc >> 31) & 1; crc = (crc << 1) & 0xFFFFFFFF
            if bit ^ c: crc ^= poly
    return crc & 0xFFFFFFFF

def calc_crc16_arib(data):
    crc = 0
    for byte in data:
        x = (byte << 8) & 0xFFFF; crc = crc ^ x
        for _ in range(8):
            if crc & 0x8000: crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else: crc = (crc << 1) & 0xFFFF
            crc &= 0xFFFF
    return crc

def calcular_reed_solomon_8bytes(data_196):
    if not HAS_REEDSOLO: return [0]*8
    try:
        rsc = RSCodec(8, c_exp=8, prim=0x11D, fcr=0)
        encoded = rsc.encode(bytes(data_196))
        return list(encoded[-8:])
    except: return [0]*8

def construir_ts_con_af_exacto(pid, cc, pes_packet):
    len_pes = len(pes_packet)
    len_af = 184 - len_pes
    if len_af < 1: pes_packet = pes_packet[:183]; len_af = 1
    af_val = len_af - 1
    af = [af_val, 0x00] + [0xFF]*(af_val-1) if af_val > 0 else [0x00]
    h = [0x47, 0x60 | (pid >> 8), pid & 0xFF, 0x30 | (cc & 0x0F)]
    return h + af + pes_packet

def encapsular_arib_onion(payload, grp_id):
    du = [0x1F, 0x20, 0x00, 0x00, len(payload)] + list(payload)
    dm = [0x3F, 0x00, 0x00, len(du)] + du
    dgl = len(dm)
    grp = [grp_id, 0x00, 0x00, (dgl >> 8) & 0xFF, dgl & 0xFF] + dm
    crc = calc_crc16_arib(grp)
    grp_fin = grp + [(crc >> 8) & 0xFF, crc & 0xFF]
    pes_py = [0x81, 0xFF, 0xF0] + grp_fin
    lpes = len(pes_py)
    return [0x00, 0x00, 0x01, 0xBF, (lpes >> 8) & 0xFF, lpes & 0xFF] + pes_py

def Precalc_Body_Forense_Datos(texto):
    cmds = [0x0C, 0x9B, 0x30, 0x20, 0x68, 0x90, 0x67, 0x90, 0x71, 0x81, 0x90, 0x51, 0x89]
    return encapsular_arib_onion(cmds + list(texto.encode('latin-1')) + [0x0D], 4)

def Precalc_Body_Forense_Gestion():
    py = [0x3F, 0x01, 0x13, 0x73, 0x70, 0x61, 0xF0]
    g_body = py + [0x00, 0x00, 0x00]
    gl = len(g_body)
    gf = [0x00, 0x00, 0x00, (gl >> 8) & 0xFF, gl & 0xFF] + g_body
    crc = calc_crc16_arib(gf)
    final = gf + [(crc >> 8) & 0xFF, crc & 0xFF]
    lpes = len([0x81, 0xFF, 0xF0] + final)
    return [0x00, 0x00, 0x01, 0xBF, (lpes >> 8) & 0xFF, lpes & 0xFF] + [0x81, 0xFF, 0xF0] + final

def Precalc_Body_Simple_Datos(texto, color, sonido):
    c = 0x87
    col = color.upper()
    if col == 'NEGRO': c = 0x80
    elif col == 'ROJO': c = 0x81
    elif col == 'VERDE': c = 0x82
    elif col == 'AMARILLO': c = 0x83
    elif col == 'AZUL': c = 0x84
    elif col == 'MAGENTA': c = 0x85
    elif col == 'CYAN': c = 0x86
    pl = [0x0C]
    if sonido: pl += [0x9B, 0x31, 0x20, 0x68]
    return encapsular_arib_onion(pl + [c, 0x89] + list(texto.encode('latin-1')) + [0x0D], 4)

def Precalc_Body_Simple_Gestion():
    py = [0x3F, 0x01, 0x1B, 0x73, 0x70, 0x61, 0xF0]
    g_body = py + [0x00, 0x00, 0x00]
    gl = len(g_body)
    gf = [0x00, 0x00, 0x00, (gl >> 8) & 0xFF, gl & 0xFF] + g_body
    crc = calc_crc16_arib(gf)
    final = gf + [(crc >> 8) & 0xFF, crc & 0xFF]
    lpes = len([0x81, 0xFF, 0xF0] + final)
    return [0x00, 0x00, 0x01, 0xBF, (lpes >> 8) & 0xFF, lpes & 0xFF] + [0x81, 0xFF, 0xF0] + final

def Precalc_Body_Clear():
    return encapsular_arib_onion([0x0C], 4)

def hackear_pmt_dinamica(pkt, pid_578, pid_1090, es_em, ver):
    pkt = list(pkt); pkt[1] |= 0x20
    ptr = pkt[4]; offset = 5 + ptr
    len_sec = ((pkt[offset+1] & 0x0F) << 8) + pkt[offset+2]
    fin = offset + 3 + len_sec - 4
    h_pmt = pkt[offset:offset+12]
    p_len = ((h_pmt[10] & 0x0F) << 8) + h_pmt[11]
    d_orig = pkt[offset+12 : offset+12+p_len]
    s_raw = pkt[offset+12+p_len : fin]
    
    b_new, d_fc = [], []
    if es_em:
        d_fc = [0xFC, 0x06, h_pmt[3], h_pmt[4], 0xBF, 0x02, 0x00, 0x1F]
        p_hi, p_lo = 0xE0 | (pid_578 >> 8), pid_578 & 0xFF
        d_e = [0x52, 0x01, 0x88, 0xFD, 0x03, 0x00, 0x08, 0x3C]
        b_new = [0x06, p_hi, p_lo, 0xF0, len(d_e)] + d_e
    else:
        p_hi, p_lo = 0xE0 | (pid_1090 >> 8), pid_1090 & 0xFF
        d_n = [0x52, 0x01, 0x88, 0xFD, 0x03, 0x00, 0x08, 0xBC]
        b_new = [0x06, p_hi, p_lo, 0xF0, len(d_n)] + d_n
    
    s_fin, ins, idx = [], False, 0
    while idx < len(s_raw):
        tipo = s_raw[idx]; il = ((s_raw[idx+3] & 0x0F) << 8) + s_raw[idx+4]; bl = 5 + il
        if tipo != 0x06: s_fin += s_raw[idx : idx+bl]
        if tipo == 0x1B and not ins: s_fin += b_new; ins = True
        idx += bl
    if not ins: s_fin += b_new
    
    h_pmt[5] = (h_pmt[5] & 0xC1) | ((ver & 0x1F) << 1)
    n_pil = len(d_orig) + len(d_fc)
    h_pmt[10] = 0xF0 | ((n_pil >> 8) & 0x0F); h_pmt[11] = n_pil & 0xFF
    t_fin = h_pmt + d_fc + d_orig + s_fin
    lt = len(t_fin) - 3 + 4
    t_fin[1] = 0xB0 | ((lt >> 8) & 0x0F); t_fin[2] = lt & 0xFF
    crc = calc_crc32_mpeg(t_fin)
    py = t_fin + [(crc >> 24) & 0xFF, (crc >> 16) & 0xFF, (crc >> 8) & 0xFF, crc & 0xFF]
    pad = 188 - 5 - len(py); pad = 0 if pad < 0 else pad
    return pkt[:5] + py + [0xFF]*pad

# =========================================================================
#  INTERFAZ GRÁFICA (GUI) RESPONSIVE
# =========================================================================

class AppEWBS:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador EWBS ISDB-T - ESPE")
        self.root.geometry("750x550")
        
        # --- Configuración Responsive Root ---
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # --- Variables ---
        self.file_in = tk.StringVar()
        self.file_out = tk.StringVar(value="Salida_EWBS.ts")
        
        self.txt_rojo = tk.StringVar(value="ALERTA SISMICA CRITICA - EVACUAR AHORA")
        self.rep_rojo = tk.IntVar(value=3)
        self.txt_amarillo = tk.StringVar(value="ALERTA LEVE - Lluvias Fuertes")
        self.rep_amarillo = tk.IntVar(value=2)
        self.txt_verde = tk.StringVar(value="ALERTA INFORMATIVA - Fin del simulacro")
        self.rep_verde = tk.IntVar(value=2)
        self.rep_clear = tk.IntVar(value=1)
        
        self.progress_val = tk.DoubleVar()
        self.status_msg = tk.StringVar(value="Esperando archivo...")

        # --- Interfaz ---
        self.create_menu()
        self.create_main_layout()
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        info_menu = tk.Menu(menubar, tearoff=0)
        info_menu.add_command(label="Acerca de", command=self.show_about)
        menubar.add_cascade(label="Información", menu=info_menu)
        self.root.config(menu=menubar)

    def create_main_layout(self):
        # Notebook principal
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Pestañas
        self.tab_config = ttk.Frame(self.notebook)
        self.tab_files = ttk.Frame(self.notebook)
        self.tab_info = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_config, text="Configuración de Mensajes")
        self.notebook.add(self.tab_files, text="Procesamiento")
        self.notebook.add(self.tab_info, text="Análisis Técnico TS")
        
        self.setup_tab_config()
        self.setup_tab_files()
        self.setup_tab_info()
        
        # Footer
        footer_frame = ttk.Frame(self.root)
        footer_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        lbl_dept = ttk.Label(footer_frame, text="Departamento de Eléctrica, Electrónica y Telecomunicaciones - ESPE", 
                             font=("Arial", 9, "bold"), foreground="#333")
        lbl_dept.pack()
        
        lbl_copy = ttk.Label(footer_frame, text="Copyright © 2026 ESPE. All Rights Reserved", 
                             font=("Arial", 8), foreground="gray")
        lbl_copy.pack()

    def setup_tab_config(self):
        # Grid weight configuration
        self.tab_config.columnconfigure(0, weight=1)
        self.tab_config.rowconfigure(0, weight=1)
        
        frame = ttk.LabelFrame(self.tab_config, text="Secuencia de Alerta", padding=15)
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        frame.columnconfigure(1, weight=1) # Columna de texto expandible
        
        # Headers
        ttk.Label(frame, text="Fase", font=("Arial", 9, "bold")).grid(row=0, column=0, pady=5)
        ttk.Label(frame, text="Texto del Mensaje", font=("Arial", 9, "bold")).grid(row=0, column=1, pady=5)
        ttk.Label(frame, text="Reps", font=("Arial", 9, "bold")).grid(row=0, column=2, pady=5)

        # 1. ROJO
        tk.Label(frame, text="1. ROJO", fg="white", bg="#D32F2F", width=12).grid(row=1, column=0, padx=5, pady=10)
        ttk.Entry(frame, textvariable=self.txt_rojo).grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Spinbox(frame, from_=0, to=50, textvariable=self.rep_rojo, width=5).grid(row=1, column=2)

        # 2. AMARILLO
        tk.Label(frame, text="2. AMARILLO", fg="black", bg="#FFEB3B", width=12).grid(row=2, column=0, padx=5, pady=10)
        ttk.Entry(frame, textvariable=self.txt_amarillo).grid(row=2, column=1, padx=5, sticky="ew")
        ttk.Spinbox(frame, from_=0, to=50, textvariable=self.rep_amarillo, width=5).grid(row=2, column=2)

        # 3. VERDE
        tk.Label(frame, text="3. VERDE", fg="white", bg="#388E3C", width=12).grid(row=3, column=0, padx=5, pady=10)
        ttk.Entry(frame, textvariable=self.txt_verde).grid(row=3, column=1, padx=5, sticky="ew")
        ttk.Spinbox(frame, from_=0, to=50, textvariable=self.rep_verde, width=5).grid(row=3, column=2)

        # 4. CLEAR
        tk.Label(frame, text="4. LIMPIEZA", fg="white", bg="black", width=12).grid(row=4, column=0, padx=5, pady=10)
        ttk.Label(frame, text="(Comando de Borrado de Pantalla)").grid(row=4, column=1)
        ttk.Spinbox(frame, from_=0, to=20, textvariable=self.rep_clear, width=5).grid(row=4, column=2)

        ttk.Label(frame, text="* Nota: Si 'Reps' es 0, la fase se omite.", font=("Arial", 8, "italic")).grid(row=5, column=0, columnspan=3, pady=20)

    def setup_tab_files(self):
        self.tab_files.columnconfigure(0, weight=1)
        
        # Frame Selección
        f_sel = ttk.LabelFrame(self.tab_files, text="Selección de Archivos", padding=15)
        f_sel.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        f_sel.columnconfigure(1, weight=1)

        ttk.Label(f_sel, text="Entrada (.ts):").grid(row=0, column=0, sticky="w")
        ttk.Entry(f_sel, textvariable=self.file_in).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(f_sel, text="Examinar", command=self.browse_in).grid(row=0, column=2)

        ttk.Label(f_sel, text="Salida (.ts):").grid(row=1, column=0, sticky="w", pady=10)
        ttk.Entry(f_sel, textvariable=self.file_out).grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Button(f_sel, text="Guardar en...", command=self.browse_out).grid(row=1, column=2)

        # Frame Ejecución
        f_run = ttk.Frame(self.tab_files, padding=10)
        f_run.grid(row=1, column=0, sticky="ew", padx=10)
        f_run.columnconfigure(0, weight=1)

        self.btn_run = ttk.Button(f_run, text="GENERAR FLUJO EWBS", command=self.start_thread)
        self.btn_run.grid(row=0, column=0, sticky="ew", ipady=10)

        ttk.Label(f_run, text="Progreso del Procesamiento:").grid(row=1, column=0, sticky="w", pady=(15,0))
        self.progress = ttk.Progressbar(f_run, variable=self.progress_val, maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew", pady=5)

        ttk.Label(f_run, textvariable=self.status_msg, font=("Arial", 10)).grid(row=3, column=0, pady=5)

    def setup_tab_info(self):
        self.tab_info.columnconfigure(0, weight=1)
        self.tab_info.rowconfigure(0, weight=1)
        
        self.txt_info = scrolledtext.ScrolledText(self.tab_info, font=("Consolas", 10), state="disabled")
        self.txt_info.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        btn_refresh = ttk.Button(self.tab_info, text="Actualizar Análisis", command=self.analyze_ts_structure)
        btn_refresh.grid(row=1, column=0, pady=5)

    def log_info(self, text):
        self.txt_info.config(state="normal")
        self.txt_info.delete(1.0, tk.END)
        self.txt_info.insert(tk.END, text)
        self.txt_info.config(state="disabled")

    def show_about(self):
        top = tk.Toplevel(self.root)
        top.title("Acerca de")
        top.geometry("450x300")
        top.resizable(False, False)
        
        f_text = ttk.Frame(top, padding=20)
        f_text.pack(expand=True)

        ttk.Label(f_text, text="Generador de Alertas EWBS ISDB-T", font=("Arial", 14, "bold")).pack(pady=5)
        ttk.Label(f_text, text="Versión 28.0 (Final)", font=("Arial", 9)).pack()
        ttk.Separator(f_text, orient="horizontal").pack(fill="x", pady=15)
        
        ttk.Label(f_text, text="Autores:", font=("Arial", 10, "bold")).pack()
        ttk.Label(f_text, text="Francisco Simbaña").pack()
        ttk.Label(f_text, text="Bryan Narvaez").pack()
        
        ttk.Label(f_text, text="\nInstitución:", font=("Arial", 10, "bold")).pack()
        ttk.Label(f_text, text="Universidad de las Fuerzas Armadas ESPE").pack()
        ttk.Label(f_text, text="Departamento de Eléctrica, Electrónica y Telecomunicaciones").pack()

        ttk.Button(top, text="Cerrar", command=top.destroy).pack(pady=20)

    # --- LÓGICA DE ANÁLISIS TÉCNICO ---
    def analyze_ts_structure(self):
        f_path = self.file_in.get()
        if not f_path or not os.path.exists(f_path):
            self.log_info("Por favor seleccione un archivo .ts válido en la pestaña 'Procesamiento'.")
            return
        
        report = f"ANÁLISIS DE ESTRUCTURA TS\nArchivo: {os.path.basename(f_path)}\n"
        report += "="*40 + "\n"
        
        pids_found = {}
        pmt_pid = "No encontrado"
        service_id = "No encontrado"
        has_iip = False
        tmcc_mode = "Desconocido"
        
        try:
            with open(f_path, 'rb') as f:
                # Leer primeros 5000 paquetes
                chunk = f.read(204 * 5000)
                num_read = len(chunk) // 204
                
                for i in range(num_read):
                    pkt = chunk[i*204 : i*204+188] # Solo header+payload
                    if pkt[0] != 0x47: continue
                    
                    pid = ((pkt[1] & 0x1F) << 8) | pkt[2]
                    pids_found[pid] = pids_found.get(pid, 0) + 1
                    
                    # PAT (PID 0)
                    if pid == 0 and service_id == "No encontrado":
                        # Parse simple de PAT para hallar PMT
                        try:
                            # Pointer field
                            ptr = pkt[4]
                            # Table ID (0x00) starts at 5 + ptr
                            offset = 5 + ptr
                            # Program number (Service ID) is at offset + 8 (header 8 bytes)
                            # Loop programs
                            # Esto es un parse muy simplificado
                            report += f"-> PAT Detectada en paquete {i}\n"
                        except: pass

                    # PMT Check (Simplificado: buscamos 0x02 table id si sabemos el pid, 
                    # o asumimos el 8136/4096 común, aquí solo reportamos lo hallado)
                    
                    # IIP (8176)
                    if pid == 8176:
                        has_iip = True
                        # Check TMCC Sync Byte (Byte 9)
                        sync = pkt[8]
                        if sync == 0x3D: tmcc_mode = "3D (Normal)"
                        elif sync == 0x3F: tmcc_mode = "3F (Alerta/Cambio)"
                        else: tmcc_mode = f"Desconocido ({hex(sync)})"

            # Generar Reporte
            report += f"IIP (PID 8176): {'DETECTADO' if has_iip else 'NO DETECTADO'}\n"
            if has_iip:
                report += f"Estado TMCC (Byte 9): {tmcc_mode}\n"
            
            report += "\nRESUMEN DE PIDS ENCONTRADOS (Muestra):\n"
            report += "PID (Dec)\tPID (Hex)\tPaquetes\tPosible Tipo\n"
            report += "-"*50 + "\n"
            
            sorted_pids = sorted(pids_found.items())
            for pid, count in sorted_pids:
                desc = "?"
                if pid == 0: desc = "PAT"
                elif pid == 8191: desc = "NULL (Relleno)"
                elif pid == 8176: desc = "IIP (TMCC)"
                elif pid == 16: desc = "NIT"
                elif pid == 17: desc = "SDT"
                elif pid == 18: desc = "EIT"
                elif pid == 20: desc = "TOT"
                elif pid == 578: desc = "EWBS (Datos Emergencia)"
                elif pid == 1090: desc = "EWBS (Datos Normales)"
                elif count > 100 and pid < 8191: desc = "Video/Audio/PMT"
                
                report += f"{pid}\t\t{hex(pid)}\t\t{count}\t\t{desc}\n"
                
            report += "\n" + "="*40 + "\n"
            report += "NOTA: Para insertar el mensaje, se utilizará:\n"
            report += " - PMT Objetivo: Se buscará automáticamente en el flujo.\n"
            report += " - PID Inserción: 578 (Rojo) y 1090 (Amarillo/Verde).\n"
            report += " - PID Relleno: 8191 (Se reemplazará por mensajes).\n"

            self.log_info(report)
            
        except Exception as e:
            self.log_info(f"Error al analizar archivo: {str(e)}")

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Transport Stream", "*.ts")])
        if f: 
            self.file_in.set(f)
            # Auto-análisis al cargar
            self.analyze_ts_structure()

    def browse_out(self):
        f = filedialog.asksaveasfilename(defaultextension=".ts", filetypes=[("Transport Stream", "*.ts")])
        if f: self.file_out.set(f)

    def start_thread(self):
        if not os.path.exists(self.file_in.get()):
            messagebox.showerror("Error", "Archivo de entrada no encontrado.")
            return
        self.btn_run.config(state="disabled")
        self.status_msg.set("Procesando... Por favor espere.")
        self.progress_val.set(0)
        t = threading.Thread(target=self.process_logic)
        t.start()

    def process_logic(self):
        try:
            SECUENCIA = [
                {'p': Precalc_Body_Forense_Datos(self.txt_rojo.get()), 
                 'g': Precalc_Body_Forense_Gestion(), 'es_rojo': True, 'reps': self.rep_rojo.get()},
                 
                {'p': Precalc_Body_Simple_Datos(self.txt_amarillo.get(), "AMARILLO", True), 
                 'g': Precalc_Body_Simple_Gestion(), 'es_rojo': False, 'reps': self.rep_amarillo.get()},
                 
                {'p': Precalc_Body_Simple_Datos(self.txt_verde.get(), "VERDE", False), 
                 'g': Precalc_Body_Simple_Gestion(), 'es_rojo': False, 'reps': self.rep_verde.get()},
                 
                {'p': Precalc_Body_Clear(), 
                 'g': Precalc_Body_Simple_Gestion(), 'es_rojo': False, 'reps': self.rep_clear.get()}
            ]
            
            TAM, BUF = 204, 5000
            PID_P, PID_N, PID_E, PID_NULL, PID_IIP = 8136, 1090, 578, 8191, 8176
            TASA, INI = 15000, 30000
            
            cc, nul, r_cnt, m_idx, i_pat = 0, 0, 0, 0, 0
            g_pkt, v_pmt = 0, 0
            
            while m_idx < len(SECUENCIA) and SECUENCIA[m_idx]['reps'] <= 0: m_idx += 1
            last_red = SECUENCIA[m_idx]['es_rojo'] if m_idx < len(SECUENCIA) else False
            
            f_path = self.file_in.get()
            tot = os.path.getsize(f_path)
            done = 0

            with open(f_path, 'rb') as fin, open(self.file_out.get(), 'wb') as fout:
                while True:
                    ch = fin.read(TAM * BUF)
                    if not ch: break
                    done += len(ch)
                    if done % (TAM*BUF*5) == 0:
                        self.root.after(0, lambda v=(done/tot)*100: self.progress_val.set(v))
                    
                    nr = len(ch) // TAM
                    ob = bytearray()
                    
                    for i in range(nr):
                        g_pkt += 1
                        off = i * TAM
                        pkt = list(ch[off : off+TAM])
                        pts = pkt[:188]; pca = pkt[188:196]
                        if pts[0] != 0x47: ob.extend(pkt); continue
                        pid = ((pts[1] & 0x1F) << 8) | pts[2]
                        mod = False
                        
                        while m_idx < len(SECUENCIA) and SECUENCIA[m_idx]['reps'] <= 0: m_idx += 1
                        
                        if m_idx < len(SECUENCIA):
                            curr = SECUENCIA[m_idx]; trg_red = curr['es_rojo']; term = False
                        else:
                            term = True; trg_red = False
                        
                        if not term and trg_red != last_red:
                            v_pmt = (v_pmt + 1) % 32; last_red = trg_red
                        
                        if term: ob.extend(pkt); continue
                        
                        if pid == PID_IIP:
                            b9 = pts[8]
                            if trg_red:
                                if b9 == 0x3D: pts[8] = 0x3F; mod = True
                            else:
                                if b9 == 0x3F: pts[8] = 0x3D; mod = True
                                
                        elif pid == PID_NULL:
                            nul += 1
                            if (g_pkt > INI) and (nul % TASA == 0):
                                pd = PID_E if trg_red else PID_N
                                py = curr['p'] if i_pat == 1 else curr['g']
                                pts = construir_ts_con_af_exacto(pd, cc, py)
                                pca[1] = (pca[1] & 0x0F) | 0x10
                                cc = (cc + 1) % 16
                                i_pat += 1
                                if i_pat > 2:
                                    r_cnt += 1; i_pat = 0
                                    if r_cnt >= curr['reps']: r_cnt = 0; m_idx += 1
                                mod = True
                                
                        elif pid == PID_P:
                            pts = hackear_pmt_dinamica(pts, PID_E, PID_N, trg_red, v_pmt)
                            mod = True
                            
                        if mod: ob.extend(pts + pca + calcular_reed_solomon_8bytes(pts + pca))
                        else: ob.extend(pkt)
                    fout.write(ob)
            
            self.root.after(0, lambda: self.status_msg.set("¡Proceso Finalizado!"))
            self.root.after(0, lambda: messagebox.showinfo("Terminado", "Archivo generado correctamente."))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.progress_val.set(100))

if __name__ == "__main__":
    root = tk.Tk()
    app = AppEWBS(root)
    root.mainloop()
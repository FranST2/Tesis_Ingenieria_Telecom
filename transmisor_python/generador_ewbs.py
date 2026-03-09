import os
import struct
import sys

# --- VERIFICACIÓN DE LIBRERÍA ---
try:
    from reedsolo import RSCodec
    HAS_REEDSOLO = True
except ImportError:
    HAS_REEDSOLO = False
    print("ADVERTENCIA: 'reedsolo' no instalado. RS será 00.")

# =========================================================================
#  UTILIDADES
# =========================================================================

def calc_crc32_mpeg(data):
    crc = 0xFFFFFFFF
    poly = 0x04C11DB7
    for byte in data:
        for i in range(7, -1, -1):
            bit_data = (byte >> i) & 1
            bit_crc = (crc >> 31) & 1
            crc = (crc << 1) & 0xFFFFFFFF
            if bit_data ^ bit_crc:
                crc ^= poly
    return crc & 0xFFFFFFFF

def calc_crc16_arib(data):
    crc = 0
    for byte in data:
        x = (byte << 8) & 0xFFFF
        crc = crc ^ x
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
            crc &= 0xFFFF
    return crc

def calcular_reed_solomon_8bytes(data_196):
    if not HAS_REEDSOLO: return [0]*8
    try:
        rsc = RSCodec(8, c_exp=8, prim=0x11D, fcr=0)
        encoded = rsc.encode(bytes(data_196))
        return list(encoded[-8:])
    except:
        return [0]*8

# =========================================================================
#  CONSTRUCTOR TS
# =========================================================================

def construir_ts_con_af_exacto(pid, cc, pes_packet):
    len_pes = len(pes_packet)
    len_af_total = 184 - len_pes
    if len_af_total < 1: pes_packet = pes_packet[:183]; len_af_total = 1
    af_val = len_af_total - 1
    af = [af_val, 0x00] + [0xFF]*(af_val-1) if af_val > 0 else [0x00]
    h1, h2, h3, h4 = 0x47, 0x60 | (pid >> 8), pid & 0xFF, 0x30 | (cc & 0x0F)
    return [h1, h2, h3, h4] + af + pes_packet

# =========================================================================
#  GENERADORES ARIB
# =========================================================================

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
    cmds = [0x0C, 0x9B, 0x30, 0x20, 0x68, 0x90, 0x67, 0x90, 0x71, 
            0x81, 0x90, 0x51, 0x89]
    payload = cmds + list(texto.encode('latin-1')) + [0x0D]
    return encapsular_arib_onion(payload, 4) 

def Precalc_Body_Forense_Gestion():
    payload_mgmt = [0x3F, 0x01, 0x13, 0x73, 0x70, 0x61, 0xF0]
    grp_body = payload_mgmt + [0x00, 0x00, 0x00]
    g_len = len(grp_body)
    grp_full = [0x00, 0x00, 0x00, (g_len >> 8) & 0xFF, g_len & 0xFF] + grp_body
    crc = calc_crc16_arib(grp_full)
    grp_final = grp_full + [(crc >> 8) & 0xFF, crc & 0xFF]
    pes_py = [0x81, 0xFF, 0xF0] + grp_final
    lpes = len(pes_py)
    return [0x00, 0x00, 0x01, 0xBF, (lpes >> 8) & 0xFF, lpes & 0xFF] + pes_py

def Precalc_Body_Simple_Datos(texto, color, sonido):
    c = 0x87
    if color == 'CYAN': c = 0x86
    elif color == 'VERDE': c = 0x82
    elif color == 'AMARILLO': c = 0x83
    payload = [0x0C]
    if sonido: payload += [0x9B, 0x31, 0x20, 0x68] 
    payload += [c, 0x89] + list(texto.encode('latin-1')) + [0x0D]
    return encapsular_arib_onion(payload, 4)

def Precalc_Body_Simple_Gestion():
    payload_mgmt = [0x3F, 0x01, 0x1B, 0x73, 0x70, 0x61, 0xF0]
    grp_body = payload_mgmt + [0x00, 0x00, 0x00]
    g_len = len(grp_body)
    grp_full = [0x00, 0x00, 0x00, (g_len >> 8) & 0xFF, g_len & 0xFF] + grp_body
    crc = calc_crc16_arib(grp_full)
    grp_final = grp_full + [(crc >> 8) & 0xFF, crc & 0xFF]
    pes_py = [0x81, 0xFF, 0xF0] + grp_final
    lpes = len(pes_py)
    return [0x00, 0x00, 0x01, 0xBF, (lpes >> 8) & 0xFF, lpes & 0xFF] + pes_py

def Precalc_Body_Clear():
    payload = [0x0C]
    return encapsular_arib_onion(payload, 4)

# =========================================================================
#  PMT
# =========================================================================

def hackear_pmt_dinamica(pkt_orig, pid_578, pid_1090, es_em, ver):
    head = list(pkt_orig[0:4]); head[1] |= 0x20
    ptr = pkt_orig[4]; offset = 5 + ptr
    len_sec = ((pkt_orig[offset+1] & 0x0F) << 8) + pkt_orig[offset+2]
    fin_tabla = offset + 3 + len_sec - 4
    tabla_raw = list(pkt_orig[offset : fin_tabla])
    
    h_pmt = tabla_raw[0:12]
    p_len = ((h_pmt[10] & 0x0F) << 8) + h_pmt[11]
    d_orig = tabla_raw[12 : 12 + p_len]
    s_raw = tabla_raw[12 + p_len :]
    
    b_new, d_fc = [], []
    if es_em:
        d_fc = [0xFC, 0x06, h_pmt[3], h_pmt[4], 0xBF, 0x02, 0x00, 0x1F]
        p_hi, p_lo = 0xE0 | (pid_578 >> 8), pid_578 & 0xFF
        d_e = [0x52, 0x01, 0x88, 0xFD, 0x03, 0x00, 0x08, 0x3C]
        b_new = [0x06, p_hi, p_lo, 0xF0, len(d_e)] + d_e
    else:
        d_fc = []
        p_hi, p_lo = 0xE0 | (pid_1090 >> 8), pid_1090 & 0xFF
        d_n = [0x52, 0x01, 0x88, 0xFD, 0x03, 0x00, 0x08, 0xBC]
        b_new = [0x06, p_hi, p_lo, 0xF0, len(d_n)] + d_n
    
    s_fin, ins, idx = [], False, 0
    while idx < len(s_raw):
        tipo = s_raw[idx]
        il = ((s_raw[idx+3] & 0x0F) << 8) + s_raw[idx+4]; bl = 5 + il
        if tipo != 0x06: s_fin += s_raw[idx : idx+bl]
        if tipo == 0x1B and not ins: s_fin += b_new; ins = True
        idx += bl
    if not ins: s_fin += b_new
    
    h_pmt[5] = (h_pmt[5] & 0xC1) | ((ver & 0x1F) << 1)
    n_pil = len(d_orig) + len(d_fc)
    h_pmt[10] = 0xF0 | ((n_pil >> 8) & 0x0F); h_pmt[11] = n_pil & 0xFF
    t_fin = h_pmt + d_fc + d_orig + s_fin
    l_tot = len(t_fin) - 3 + 4
    t_fin[1] = 0xB0 | ((l_tot >> 8) & 0x0F); t_fin[2] = l_tot & 0xFF
    crc = calc_crc32_mpeg(t_fin)
    py = t_fin + [(crc >> 24) & 0xFF, (crc >> 16) & 0xFF, (crc >> 8) & 0xFF, crc & 0xFF]
    pad = 188 - 5 - len(py); pad = 0 if pad < 0 else pad
    return head + [ptr] + py + [0xFF]*pad

# =========================================================================
#  MAIN LOOP
# =========================================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    archivo_entrada = os.path.join(script_dir, 'ECTV_BTS.ts')
    archivo_salida = os.path.join(script_dir, 'Alerta_Salida_V26_ZeroSkip.ts')
    
    if not os.path.exists(archivo_entrada): return
    TAM_FULL, BUFFER_SIZE = 204, 5000
    PID_PMT, PID_NORMAL, PID_EMERGENCIA, PID_NULL, PID_IIP = 8136, 1090, 578, 8191, 8176
    
    print("PROCESADOR V26 - AUTO-SKIP ZERO REPS")
    
    # EJEMPLO: Si pones 'reps': 0 en ROJO, NO saldrá ni sonará.
    
    M_ROJO = {
        'p': Precalc_Body_Forense_Datos("ALERTA SISMICA CRITICA - EVACUAR AHORA"), 
        'g': Precalc_Body_Forense_Gestion(), 
        'es_rojo': True, 'reps': 3
    }
    
    M_AMARILLO = {
        'p': Precalc_Body_Simple_Datos("ALERTA LEVE - Lluvias Fuertes", "AMARILLO", True), 
        'g': Precalc_Body_Simple_Gestion(), 
        'es_rojo': False, 'reps': 2
    }
    
    M_VERDE = {
        'p': Precalc_Body_Simple_Datos("ALERTA INFORMATIVA - Fin del simulacro", "VERDE", False), 
        'g': Precalc_Body_Simple_Gestion(), 
        'es_rojo': False, 'reps': 2
    }
    
    M_CLEAR = {
        'p': Precalc_Body_Clear(), 
        'g': Precalc_Body_Simple_Gestion(), 
        'es_rojo': False, 'reps': 1
    }
    
    SECUENCIA = [M_ROJO, M_AMARILLO, M_VERDE, M_CLEAR]
    
    cc_ewbs, cont_nulos, rep_cnt, msg_idx = 0, 0, 0, 0
    idx_patron = 0
    TASA_INSERCION, INICIO = 15000, 30000
    
    global_pkt = 0
    version_pmt = 0
    
    # Inicializar estado correcto saltando mensajes 0
    # Esto evita que el estado inicial sea erróneo si el primero es 0 reps
    dummy_idx = 0
    while dummy_idx < len(SECUENCIA) and SECUENCIA[dummy_idx]['reps'] <= 0:
        dummy_idx += 1
    
    if dummy_idx < len(SECUENCIA):
        ultimo_estado_rojo = SECUENCIA[dummy_idx]['es_rojo']
    else:
        ultimo_estado_rojo = False # Todos son 0 o vacíos
    
    try:
        with open(archivo_entrada, 'rb') as fin, open(archivo_salida, 'wb') as fout:
            while True:
                chunk = fin.read(TAM_FULL * BUFFER_SIZE)
                if not chunk: break
                num_read = len(chunk) // TAM_FULL
                out_buffer = bytearray()
                
                for i in range(num_read):
                    global_pkt += 1
                    off = i * TAM_FULL
                    pkt = list(chunk[off : off + TAM_FULL])
                    pts = pkt[0:188]; pcapas = pkt[188:196]
                    if pts[0] != 0x47: out_buffer.extend(pkt); continue
                    pid = ((pts[1] & 0x1F) << 8) | pts[2]
                    modif = False
                    
                    # --- LÓGICA DE SALTO AUTOMÁTICO (AUTO-SKIP) ---
                    # Si el mensaje actual tiene 0 repeticiones, saltar al siguiente
                    while msg_idx < len(SECUENCIA) and SECUENCIA[msg_idx]['reps'] <= 0:
                        msg_idx += 1
                    
                    # --- ESTADO GLOBAL ---
                    if msg_idx < len(SECUENCIA):
                        curr = SECUENCIA[msg_idx]
                        target_red = curr['es_rojo']
                        secuencia_terminada = False
                    else:
                        secuencia_terminada = True
                        target_red = False
                    
                    if not secuencia_terminada:
                        if target_red != ultimo_estado_rojo:
                            version_pmt = (version_pmt + 1) % 32
                            ultimo_estado_rojo = target_red
                    
                    if secuencia_terminada:
                        out_buffer.extend(pkt); continue
                        
                    # 1. IIP
                    if pid == PID_IIP:
                        byte9 = pts[8]
                        if target_red:
                            if byte9 == 0x3D: pts[8] = 0x3F; modif = True
                        else:
                            if byte9 == 0x3F: pts[8] = 0x3D; modif = True
                    
                    # 2. INYECCIÓN
                    elif pid == PID_NULL:
                        cont_nulos += 1
                        if (global_pkt > INICIO) and (cont_nulos % TASA_INSERCION == 0):
                            p_dest = PID_EMERGENCIA if target_red else PID_NORMAL
                            payload = curr['p'] if idx_patron == 1 else curr['g']
                            pts = construir_ts_con_af_exacto(p_dest, cc_ewbs, payload)
                            pcapas[1] = (pcapas[1] & 0x0F) | 0x10
                            cc_ewbs = (cc_ewbs + 1) % 16
                            
                            idx_patron += 1
                            if idx_patron > 2: 
                                rep_cnt += 1; idx_patron = 0
                                if rep_cnt >= curr['reps']: 
                                    rep_cnt = 0; msg_idx += 1
                            modif = True
                            
                    # 3. PMT
                    elif pid == PID_PMT:
                        pts = hackear_pmt_dinamica(pts, PID_EMERGENCIA, PID_NORMAL, target_red, version_pmt)
                        modif = True
                        
                    if modif:
                        blk = pts + pcapas
                        out_buffer.extend(blk + calcular_reed_solomon_8bytes(blk))
                    else:
                        out_buffer.extend(pkt)
                fout.write(out_buffer)
        print(f"\n¡LISTO! {os.path.basename(archivo_salida)}")
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()
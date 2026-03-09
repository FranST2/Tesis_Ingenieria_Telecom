% *************** Analizador de PID y Decodificador PAT *****************
% 
%    Nombre: Simbaña Tasiguano Francisco Alejandro
%    Materia: Televisión Digital
%************************************************************************
clear; 
clc; 

%% Nombre y manejo del archivo
entrada = 'Alerta_Salida_Corregida_V9_Py.ts';
Archivo = fopen(entrada, 'r'); 

if Archivo == -1
    error('No se pudo abrir el archivo. Verifica el nombre o la ruta.');
end

info = dir(entrada); 
nBytes = info.bytes; 
tamP = 204; % Tamaño de paquete (204 indica formato BTS/ISDB-T) [cite: 6380]
npac = floor(nBytes / tamP);

% Vector para almacenar los PIDs
valoresPIDs = zeros(1, npac);
pat_analizada = false; % Bandera para analizar la PAT solo una vez

fprintf('Iniciando análisis de %d paquetes...\n', npac);

%% Procesamiento de paquetes TS
for n = 1:npac
    % Desplazamiento y lectura del paquete
    des = (n - 1) * tamP; 
    fseek(Archivo, des, 'bof'); 
    
    % Leer el paquete completo (array de 204 bytes)
    paquete = fread(Archivo, tamP, 'uint8'); 
    
    % Extraer el PID mediante la función (bytes 2 y 3 del header)
    [PID_D, ~] = obtenerPID(paquete);
    valoresPIDs(n) = PID_D; 
    
    % --- MÓDULO DE ANÁLISIS DE LA PAT (PID 0) ---
    % Si encontramos el PID 0 y aún no lo hemos analizado:
    if PID_D == 0 && ~pat_analizada
        fprintf('\n>>> PAT Encontrada en el paquete #%d <<<\n', n);
        analizarPAT(paquete); % Llamamos a la función de análisis detallado
        pat_analizada = true; % Marcamos como visto para no repetir
    end
end

%% Análisis de PIDs únicos
[PID_Un, ~, ~] = unique(valoresPIDs); 
f = histc(valoresPIDs, PID_Un); 
porc = (f / npac) * 100; 

%% Resultados Estadísticos
fprintf('\n================ RESUMEN DE PIDs ================\n');
fprintf('|   PID (Dec/Hex)   |  Paquetes  | Porcentaje |\n');
fprintf('=================================================\n');
for i = 1:length(PID_Un)
    fprintf('| %4d / 0x%04X    | %6d     |   %5.2f%%   |\n', ...
        PID_Un(i), PID_Un(i), f(i), porc(i));
end
fprintf('=================================================\n');

ft = sum(f);
fprintf('Total de paquetes analizados: %d\n', ft);
fclose(Archivo); 

%% ---------------------------------------------------------
%  FUNCIONES AUXILIARES
%  ---------------------------------------------------------

% Función original para obtener el PID de la cabecera TS
function [PID_D, PID_H] = obtenerPID(cadena)
    byte2 = dec2hex(cadena(2), 2); 
    byte3 = dec2hex(cadena(3), 2); 
    pd = byte2(1); 
    
    % Máscara para obtener los últimos 5 bits del byte 2 (0x1F)
    % PID son 13 bits: 5 bits del byte2 + 8 bits del byte3
    val_byte2 = bitand(cadena(2), 31); 
    
    PID_D = val_byte2 * 256 + cadena(3);
    PID_H = dec2hex(PID_D, 4);
end

% --- NUEVA FUNCIÓN: ANALIZADOR DE LA TABLA PAT ---
% Basado en la estructura definida en [cite: 223, 247]
function analizarPAT(paquete)
    % 1. Verificar PUSI (Payload Unit Start Indicator) - Bit 6 del Byte 2 (0x40)
    % Si es 1, hay un byte de puntero (Pointer Field) al inicio del payload.
    pusi = bitand(paquete(2), 64) > 0;
    
    % La cabecera TS son 4 bytes. El payload empieza en el 5.
    indice = 5;
    
    if pusi
        puntero = paquete(indice);
        indice = indice + 1 + puntero; % Saltamos el Puntero y lo que indique
    end
    
    % Ahora 'indice' apunta al inicio de la Tabla PAT (Table ID)
    
    % 2. Lectura de Cabecera de la Tabla
    table_id = paquete(indice); % Debe ser 0x00 para PAT
    if table_id ~= 0
        fprintf('Error: El Table ID no es 0x00, no es una PAT válida.\n');
        return;
    end
    
    % Longitud de la sección (12 bits): últimos 4 bits de byte2 + byte3
    % Diagrama "Section Length" [cite: 218]
    sec_len_b1 = bitand(paquete(indice+1), 15); % Máscara 0x0F
    sec_len_b2 = paquete(indice+2);
    section_length = sec_len_b1 * 256 + sec_len_b2;
    
    transport_stream_id = paquete(indice+3) * 256 + paquete(indice+4);
    
    fprintf('  -> Transport Stream ID: %d (0x%04X)\n', transport_stream_id, transport_stream_id);
    fprintf('  -> Longitud de Sección: %d bytes\n', section_length);
    
    % 3. Bucle de Programas (El corazón de la PAT)
    % Los datos de programas empiezan en el byte 9 de la tabla (indice + 8)
    % Terminan antes del CRC (los últimos 4 bytes de la sección)
    
    inicio_lista = indice + 8;
    fin_lista = (indice + 2 + section_length) - 4; % -4 por el CRC
    
    fprintf('  ---------------------------------------------\n');
    fprintf('  |  Programa (ID)  |  PID Destino (PMT/NIT) |\n');
    fprintf('  ---------------------------------------------\n');
    
    % Recorremos cada entrada de 4 bytes [cite: 223, 242]
    for k = inicio_lista : 4 : (fin_lista - 1)
        % Bytes 1-2: Program Number
        prog_num = paquete(k) * 256 + paquete(k+1);
        
        % Bytes 3-4: PID (Los 3 primeros bits son reservados '111', máscara 0x1FFF)
        raw_pid_val = paquete(k+2) * 256 + paquete(k+3);
        prog_pid = bitand(raw_pid_val, 8191); % 8191 es 0x1FFF
        
        if prog_num == 0
            % Si Program Number es 0, es la NIT (Network Information Table) [cite: 228]
            fprintf('  |  0000 (NIT)     |  PID %4d (0x%04X)      |\n', prog_pid, prog_pid);
        else
            % Si no es 0, es un Programa y el PID apunta a su PMT [cite: 242]
            fprintf('  |  %4d (0x%04X)   |  PID %4d (0x%04X) (PMT)|\n', prog_num, prog_num, prog_pid, prog_pid);
        end
    end
    fprintf('  ---------------------------------------------\n');
    
    % 4. Mostrar CRC-32 (Últimos 4 bytes) [cite: 239]
    crc1 = paquete(fin_lista+1);
    crc2 = paquete(fin_lista+2);
    crc3 = paquete(fin_lista+3);
    crc4 = paquete(fin_lista+4);
    fprintf('  -> CRC-32: %02X %02X %02X %02X\n', crc1, crc2, crc3, crc4);
    
    % 5. Análisis BTS (Últimos 16 bytes del paquete 204) [cite: 6380]
    if length(paquete) == 204
        bts_control = paquete(189:196);
        reed_solomon = paquete(197:204);
        fprintf('\n  [Info Extra BTS]\n');
        fprintf('  -> Control ISDB-T (Hex): ');
        fprintf('%02X ', bts_control);
        fprintf('\n  -> Reed-Solomon (Hex):   ');
        fprintf('%02X ', reed_solomon);
        fprintf('\n');
    end
    fprintf('\n');
end
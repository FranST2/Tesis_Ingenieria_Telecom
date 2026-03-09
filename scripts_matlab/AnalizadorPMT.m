% *************** REPORTE DE EVOLUCIÓN DE LA PMT (PID 4096) *************
%    Rastrea cambios en la estructura del canal (Video, Audio, Datos).
%    Agrupa por Versión y Contenido.
% ***********************************************************************
clear; 
clc; 

%% 1. Configuración
entrada = 'Alerta_Salida_Corregida_V9_Py.ts'; 
pid_objetivo = 8136; % PID de la PMT a analizar
tamP = 204;          % Formato BTS

Archivo = fopen(entrada, 'r');
if Archivo == -1
    error('No se pudo abrir el archivo.');
end

info = dir(entrada); 
nBytes = info.bytes; 
npac = floor(nBytes / tamP);

fprintf('Analizando %d paquetes buscando PMT (PID %d)...\n', npac, pid_objetivo);
fprintf('================================================================================================================\n');
fprintf('| VER | P. INICIO   | P. FINAL    | CANTIDAD | DETALLE (Tipo -> PID)                                            \n');
fprintf('================================================================================================================\n');

%% 2. Variables de Estado
estado.activo = false;
estado.datos = [];      % Bytes de carga útil para comparar igualdad exacta
estado.version = -1;    
estado.inicio = -1;     
estado.fin = -1;        
estado.conteo = 0;      
estado.info_str = '';   

%% 3. Bucle Principal
for n = 1:npac
    % Leer paquete
    des = (n - 1) * tamP;
    fseek(Archivo, des, 'bof');
    paquete = fread(Archivo, tamP, 'uint8');
    
    % Obtener PID
    pid = bitand(paquete(2), 31) * 256 + paquete(3);
    
    if pid == pid_objetivo
        % Verificar Puntero (PUSI) para asegurar que es inicio de tabla
        pusi = bitand(paquete(2), 64) > 0;
        
        if pusi
            % Extraer datos útiles para comparar (evitamos cabecera TS y cola BTS)
            datos_utiles = paquete(5:188); 
            
            % Decodificar info legible
            [version, info_streams] = decodificarInfoPMT(paquete);
            
            if ~estado.activo
                % Primer paquete encontrado
                estado.activo = true;
                estado.datos = datos_utiles;
                estado.version = version;
                estado.inicio = n;
                estado.fin = n;
                estado.conteo = 1;
                estado.info_str = info_streams;
                
            elseif isequal(estado.datos, datos_utiles)
                % Paquete idéntico -> Continuidad
                estado.conteo = estado.conteo + 1;
                estado.fin = n;
                
            else
                % Paquete diferente -> Cambio de Versión/Contenido
                imprimirFila(estado);
                
                % Reset de estado
                estado.datos = datos_utiles;
                estado.version = version;
                estado.inicio = n;
                estado.fin = n;
                estado.conteo = 1;
                estado.info_str = info_streams;
            end
        else
            % Si es un paquete de continuación (muy largo), lo contamos en el bloque actual
            if estado.activo
                estado.conteo = estado.conteo + 1;
                estado.fin = n;
            end
        end
    end
end

% Imprimir último bloque
if estado.activo
    imprimirFila(estado);
else
    fprintf('No se encontraron paquetes con PID %d.\n', pid_objetivo);
end

fprintf('================================================================================================================\n');
fclose(Archivo);


%% ---------------------------------------------------------
%  FUNCIONES AUXILIARES
%  ---------------------------------------------------------

function imprimirFila(estado)
    fprintf('| %3d | %-11d | %-11d | %-8d | %s\n', ...
        estado.version, ...
        estado.inicio, ...
        estado.fin, ...
        estado.conteo, ...
        estado.info_str);
end

function [version, texto_streams] = decodificarInfoPMT(pkt)
    % Parsear Puntero
    offset = 5;
    puntero = pkt(offset);
    offset = offset + 1 + puntero;
    
    % Verificar Table ID (Debe ser 0x02 para PMT)
    if pkt(offset) ~= 2
        version = -1;
        texto_streams = 'Error: No es tabla PMT';
        return;
    end
    
    % Versión
    ver_byte = pkt(offset+5);
    version = bitshift(bitand(ver_byte, 62), -1);
    
    % Longitud de sección
    sec_len = bitand(pkt(offset+1), 15) * 256 + pkt(offset+2);
    
    % PCR PID
    pcr_pid = bitand(pkt(offset+8), 31) * 256 + pkt(offset+9);
    
    % Longitud Info Programa
    prog_info_len = bitand(pkt(offset+10), 15) * 256 + pkt(offset+11);
    
    % Inicio de Streams
    cursor = offset + 12 + prog_info_len;
    fin_tabla = offset + 2 + sec_len - 4; % -4 CRC
    
    lista = sprintf('PCR(%d)', pcr_pid);
    
    while cursor < fin_tabla
        stype = pkt(cursor);
        epid = bitand(pkt(cursor+1), 31) * 256 + pkt(cursor+2);
        es_info_len = bitand(pkt(cursor+3), 15) * 256 + pkt(cursor+4);
        
        desc_tipo = obtenerNombreStream(stype);
        lista = [lista, sprintf(', %s(%d)', desc_tipo, epid)];
        
        cursor = cursor + 5 + es_info_len;
    end
    texto_streams = lista;
end

function nombre = obtenerNombreStream(type)
    switch type
        case 1, nombre = 'MPEG1-Vid';
        case 2, nombre = 'MPEG2-Vid';
        case 3, nombre = 'MPEG1-Aud';
        case 4, nombre = 'MPEG2-Aud';
        case 6, nombre = 'Datos/Subt';
        case 15, nombre = 'AAC';      % ADTS
        case 17, nombre = 'AAC-LATM';
        case 27, nombre = 'H.264';
        case 13, nombre = 'DSM-CC';
        otherwise, nombre = sprintf('Type 0x%02X', type);
    end
end
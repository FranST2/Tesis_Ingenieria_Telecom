% *************** Analizador de Alertas EWBS (Basado en V8) ***********
% 
%    Nombre:
%    Simbaña Tasiguano Francisco Alejandro
%    NRC: 5733
%************************************************************************
clear; % Limpiar el entorno de trabajo
clc; % Limpiar la consola

%% Nombre y manejo del archivo
entrada = 'Alerta_Salida_Corregida_V9_Py.ts';
Archivo = fopen(entrada, 'r'); % Apertura en modo lectura
info = dir(entrada); % Información del archivo
nBytes = info.bytes; % Total de bytes en el archivo
tamP = 204; % Tamaño de un paquete TS estándar
npac = floor(nBytes / tamP);
%npac = nBytes / tamP; % Número de paquetes TS

% Vector para almacenar los PIDs
valoresPIDs = zeros(1, npac);

%%PID reconocidos 
TAGde1=1090;
TAGde2=578;
SIGNATURE_BYTES = [0x1F, 0x20, 0x00, 0x00];
BYTE_INICIO = 0x0C;
BYTE_FIN    = 0x89;

%% --- 3. Almacenamiento de Resultados (Nuevo) ---
foundPIDs_Msg = []; % PID del paquete con el mensaje
foundPackets_Msg = []; % N° de paquete
foundMessages_Msg = {};% El texto del mensaje
%% Procesamiento de paquetes TS
for n = 1:npac
    % Desplazamiento y lectura del paquete
    des = (n - 1) * tamP; % Calcular desplazamiento
    fseek(Archivo, des, 'bof'); % Mover el puntero en el archivo
    cadena = fread(Archivo, tamP); % Leer un paquete (en valores decimal)
    cadenaH = dec2hex(cadena); % En hexadecimal
    % Extraer el PID mediante la funcion 
    [PID_D, ~] = obtenerPID(cadena);
    valoresPIDs(n) = PID_D; % Almacenar el PID decimal
   if (PID_D == TAGde1)||(PID_D == TAGde2)
        %fprintf('Entro el ciclo for');
        indices = strfind(cadena', SIGNATURE_BYTES); 
        if (~isempty(indices)) && (cadena(5,1)~=157)
            %fprintf('Encuentro la firma');
            % ¡Firma encontrada!
            pos_i = find(cadena == BYTE_INICIO);
            pos_f = find(cadena == BYTE_FIN);
            idx_i = pos_i(1);
            idx_f = pos_f(1);
            if idx_i < idx_f
                % --- 4. Cálculo de la distancia (Conteo) ---
                % (Fin - Inicio) + 1
                % Se suma 1 para que el conteo incluya ambos extremos.
                % Ejemplo: (10 - 4) + 1 = 7
                Dis_b = (idx_f - idx_i) + 1;
                %fprintf('¡Orden correcto! Conteo total (inclusivo): %d bytes.\n', cantidad_bytes);
                % Opcional: Extraer solo ese segmento
                %segmento_rojo = cadena(idx_inicio : idx_fin);
                %disp('Segmento extraído:');
                %disp(segmento_rojo);
            else
                % Si idx_inicio es >= idx_fin
                fprintf('Error de orden: El byte de FIN (índice %d) aparece ANTES que el de INICIO (índice %d).\n', ...
                        idx_f, idx_i);
            end
            % (k) es la posición del 0x1F
            k = indices(1); 
            % El byte (k+4) es la Longitud (L)
            Lp=k+4;
            % Nos aseguramos de que no sea un error y esté dentro del paquete
            if (Lp) <= length(cadena)
                
                % L = Tamaño total (palabra + 0x0D)
                L = cadena(k + 4); 
    
                % Verificamos que la longitud sea válida
                % (mayor que 0 y que no se salga del paquete)
                if L > 0 && (k + 4 + L) <= length(cadena)
                    
                    % El mensaje es de (k+5) hasta (k+4+L-1)
                    msg_start = Lp + Dis_b+1;
                    msg_end = k + 4 + L - 1; % El último byte (k+4+L) es el 0x0D
    
                    % Extraer el mensaje
                    messageBytes = cadena(msg_start : msg_end);
                    alertMessage = char(messageBytes');
                    % Guardar resultados
                    foundPIDs_Msg(end+1) = PID_D;
                    foundPackets_Msg(end+1) = n;
                    foundMessages_Msg{end+1} = alertMessage;
                    
                end
            end
        end
    end
end

%% Análisis de PIDs únicos
[PID_Un, ~, grupos] = unique(valoresPIDs); % Extrae valores únicos, en este caso los PID
f = histc(valoresPIDs, PID_Un); % Frecuencias/Cantidad de repeticiones
porc = (f / npac) * 100; % Resultados finales en porcentajes

%% Resultados

for i = 1:length(PID_Un)
    fprintf('PID %d/0x%s   || %d paquetes   ||  %.2f%%.\n', ...
        PID_Un(i),dec2hex(PID_Un(i)), f(i), porc(i));
end
ft=sum(f);
porct=sum(porc);
fprintf('Total de paquetes %d\n',ft);
fprintf('Porcentaje total %.2f%%.\n',porct);

fclose(Archivo); % Cerrar el archivo

%% Función para obtener el PID
function [PID_D, PID_H] = obtenerPID(cadena)
    % Leer los bytes relevantes
    byte2 = dec2hex(cadena(2), 2); % Segundo byte en hexadecimal
    byte3 = dec2hex(cadena(3), 2); % Tercer byte en hexadecimal

    % Evaluar paridad del primer dígito hexadecimal de byte2
    pd = byte2(1); %Primero dígito del byte2
    if mod(hex2dec(pd), 2) == 0 %El módulo devuelve el resto por lo que al ser par debe ser 0 y cualquier otro valor será impar
        bitA = '0'; 
    else
        bitA = '1';
    end

    % Concatenar bit adicional con los tres símbolos restantes
    PID_H = [bitA, byte2(2), byte3];
    PID_D = hex2dec(PID_H); % Convertir a decimal
end
% *************** Analizador de PID *************************************
% 
%    Nombre:
%    Simbaña Tasiguano Francisco Alejandro
%    NRC: 5733
%************************************************************************
clear; % Limpiar el entorno de trabajo
clc; % Limpiar lEn esa consola

%% Nombre y manejo del archivo
entrada = 'PRUEBA_MASTER_FIX.ts';
Archivo = fopen(entrada, 'r'); % Apertura en modo lectura
info = dir(entrada); % Información del archivo
nBytes = info.bytes; % Total de bytes en el archivo
tamP = 188; % Tamaño de un paquete TS estándar
npac = floor(nBytes / tamP);
%npac = nBytes / tamP; % Número de paquetes TS

% Vector para almacenar los PIDs
valoresPIDs = zeros(1, npac);

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
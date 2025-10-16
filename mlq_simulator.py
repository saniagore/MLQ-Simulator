import os
from collections import deque

class Process:
    """
    Representa un proceso con sus atributos y métricas de planificación.
    """
    def __init__(self, pid, burst_time, arrival_time, queue_num, priority):
        self.pid = pid
        self.burst_time = burst_time
        self.arrival_time = arrival_time
        self.queue_num = queue_num
        self.priority = priority
        self.remaining_time = burst_time
        self.first_run_time = -1
        self.completion_time = 0
        self.turnaround_time = 0
        self.waiting_time = 0
        self.response_time = 0

    def __repr__(self):
        return (f"Process(pid={self.pid}, bt={self.burst_time}, at={self.arrival_time}, "
                f"q={self.queue_num}, prio={self.priority})")

class MLQSimulator:
    """
    Orquesta la simulación del algoritmo de planificación de colas multinivel (MLQ).
    """
    def __init__(self, quantum1=3, quantum2=5):
        self.quantum1 = quantum1
        self.quantum2 = quantum2
        self.q1 = deque()
        self.q2 = deque()
        self.q3 = []
        self.processes_to_arrive = []
        self.completed_processes = []
        self.current_time = 0
        self.current_process = None

    def load_processes(self, file_path):
        """
        Carga los procesos desde un archivo de texto.
        """
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    # Ignorar comentarios y líneas vacías
                    if line.startswith('#') or not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(';')]
                    if len(parts) == 5:
                        pid, bt_str, at_str, q_num_str, prio_str = parts
                        self.processes_to_arrive.append(Process(pid, int(bt_str), int(at_str), int(q_num_str), int(prio_str)))
            self.processes_to_arrive.sort(key=lambda p: p.arrival_time)
            return True
        except FileNotFoundError:
            print(f"Error: El archivo '{file_path}' no fue encontrado.")
            return False
        except Exception as e:
            print(f"Error al procesar el archivo '{file_path}': {e}")
            return False

    def run_simulation(self):
        """
        Ejecuta el ciclo principal de la simulación.
        """
        while self.processes_to_arrive or self.q1 or self.q2 or self.q3 or self.current_process:
            self.check_for_arriving_processes()
            
            if not self.current_process:
                self.select_next_process()

            if self.current_process:
                self.execute_process()
            else:
                self.current_time += 1

    def check_for_arriving_processes(self):
        """Mueve procesos que han llegado a sus colas correspondientes."""
        while self.processes_to_arrive and self.processes_to_arrive[0].arrival_time <= self.current_time:
            process = self.processes_to_arrive.pop(0)
            if process.queue_num == 1:
                self.q1.append(process)
            elif process.queue_num == 2:
                self.q2.append(process)
            elif process.queue_num == 3:
                self.q3.append(process)

    def select_next_process(self):
        """Selecciona el siguiente proceso a ejecutar basado en la jerarquía de colas."""
        if self.q1:
            self.current_process = self.q1.popleft()
        elif self.q2:
            self.current_process = self.q2.popleft()
        elif self.q3:
            # La cola SJF sí se ordena por burst time y usa la prioridad como desempate.
            self.q3.sort(key=lambda p: (p.burst_time, -p.priority))
            self.current_process = self.q3.pop(0)

    def execute_process(self):
        """Simula la ejecución del proceso actual."""
        process = self.current_process
        
        if process.first_run_time == -1:
            process.first_run_time = self.current_time

        quantum = float('inf') # Por defecto para SJF
        if process.queue_num == 1:
            quantum = self.quantum1
        elif process.queue_num == 2:
            quantum = self.quantum2

        run_time = min(quantum, process.remaining_time)
        self.current_time += run_time
        process.remaining_time -= run_time

        self.check_for_arriving_processes() # Revisa si llegaron procesos durante la ejecución

        if process.remaining_time == 0:
            self.finalize_process(process)
            self.current_process = None
        else: # Si el proceso no ha terminado (debe ser de Q1 o Q2)
            if self.q1: # Si llega un proceso de alta prioridad
                 if process.queue_num == 1: self.q1.append(process)
                 elif process.queue_num == 2: self.q2.append(process)
                 self.current_process = None # Forzar re-selección
            else:
                 # Si no, simplemente se re-encola en su propia cola
                 if process.queue_num == 1: self.q1.append(process)
                 elif process.queue_num == 2: self.q2.append(process)
                 self.current_process = None


    def finalize_process(self, process):
        """Calcula las métricas finales para un proceso completado."""
        process.completion_time = self.current_time
        process.turnaround_time = process.completion_time - process.arrival_time
        process.waiting_time = process.turnaround_time - process.burst_time
        process.response_time = process.first_run_time - process.arrival_time
        self.completed_processes.append(process)

    def write_output(self, input_path, output_path):
        """Escribe los resultados de la simulación en un archivo de salida."""
        self.completed_processes.sort(key=lambda p: p.pid)
        
        total_wt, total_ct, total_rt, total_tat = 0, 0, 0, 0
        num_processes = len(self.completed_processes)

        # Solo intenta crear el directorio si el path de salida realmente contiene una carpeta.
        output_dir = os.path.dirname(output_path)
        if output_dir: # Esta condición evita el error cuando la ruta está vacía.
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(f"#archivo: {os.path.basename(input_path)}\n")
            f.write("#etiqueta; BT; AT; Q; Pr; WT; CT; RT; TAT\n")
            
            for p in self.completed_processes:
                f.write(f"{p.pid};{p.burst_time};{p.arrival_time};{p.queue_num};{p.priority};"
                        f"{p.waiting_time};{p.completion_time};{p.response_time};{p.turnaround_time}\n")
                total_wt += p.waiting_time
                total_ct += p.completion_time
                total_rt += p.response_time
                total_tat += p.turnaround_time

            if num_processes > 0:
                avg_wt = total_wt / num_processes
                avg_ct = total_ct / num_processes
                avg_rt = total_rt / num_processes
                avg_tat = total_tat / num_processes
                f.write(f"$WT={avg_wt:.1f}; $CT={avg_ct:.1f}; $RT={avg_rt:.1f}; $TAT={avg_tat:.1f};\n")


def main():
    input_filename = "mlq001.txt"
    output_filename = f"{os.path.splitext(input_filename)[0]}_output.txt"

    # Crear un archivo de entrada de ejemplo si no existe
    if not os.path.exists(input_filename):
        print(f"Creando archivo de entrada de ejemplo: {input_filename}")
        with open(input_filename, "w") as f:
            f.write("#etiqueta; burst time (BT); arrival time (AT); Queue (Q): Priority(5>1)\n")
            f.write("A;6;0;1;5\n")
            f.write("B;9;0;1;4\n")
            f.write("C;10;0;2;3\n")
            f.write("D;15;0;2;3\n")
            f.write("E;8;0;3;2\n")

    simulator = MLQSimulator()
    if simulator.load_processes(input_filename):
        simulator.run_simulation()
        simulator.write_output(input_filename, output_filename)
        print(f"Simulación completada. Resultados en '{output_filename}'.")

if __name__ == "__main__":
    main()
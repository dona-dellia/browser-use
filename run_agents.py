import subprocess

NUM_INSTANCES = 2
processes = []

for i in range(NUM_INSTANCES):
    print(f"Iniciando instância {i}...")
    proc = subprocess.Popen(
        ['python', 'agent_runner.py', str(i)]
    )
    processes.append(proc)

# Aguarda todas as instâncias terminarem
for i, proc in enumerate(processes):
    proc.wait()
    print(f"Instância {i} finalizada com código {proc.returncode}")

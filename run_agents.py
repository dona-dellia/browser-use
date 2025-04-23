import subprocess
import time

NUM_INSTANCES = 30
MAX_CONCURRENT = 5     # Quantos processos simultâneos
MAX_RETRIES = 2        # Tentativas máximas por instância

def run_instance(instance_id, attempt):
    print(f"➡️  Iniciando Instância {instance_id} | Tentativa {attempt + 1}")
    proc = subprocess.Popen(
        ['python', 'agent_runner.py', str(instance_id)]
    )
    return proc

def main():
    pending = {i: 0 for i in range(NUM_INSTANCES)} 
    running = []

    while pending or running:
        while len(running) < MAX_CONCURRENT and pending:
            instance_id, attempts = pending.popitem()
            proc = run_instance(instance_id, attempts)
            running.append((instance_id, attempts, proc))

        for instance in running[:]:
            instance_id, attempts, proc = instance
            ret = proc.poll()
            if ret is not None:
                running.remove(instance)
                if ret == 0:
                    print(f"✅ Instância {instance_id} finalizada com sucesso.")
                else:
                    print(f"⚠️  Instância {instance_id} falhou (código {ret}).")
                    if attempts + 1 < MAX_RETRIES:
                        pending[instance_id] = attempts + 1
                        print(f"🔄 Reenfileirando Instância {instance_id} para nova tentativa.")
                    else:
                        print(f"❌ Instância {instance_id} atingiu o máximo de tentativas.")

        time.sleep(1) 

    print("\n🎉 Todas as instâncias foram processadas.")

if __name__ == '__main__':
    main()

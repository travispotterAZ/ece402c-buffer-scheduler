# Author: Andrew Kostick
# This script runs a series of benchmarks by starting the server with different scheduling policies and buffer replacement algorithms

import subprocess
import time

# Define the scheduling policies and buffer replacement algorithms to test
policies = ['fcfs', 'rr', 'priority']
algorithms = ['fifo', 'lru', 'two_list']

results = []

# Going through each scheduling policy and buffer replacement algorithm, starting the server, running a client query, 
# and recording the response time and output. The it prints the results at the end.
for policy in policies:
    for algorithm in algorithms:
        print(f"Running: policy={policy} algorithm={algorithm}")

        start = time.time()
        server = subprocess.Popen(
            ['python', 'main.py', '--policy', policy, '--algorithm', algorithm, '--frames', '32'],
        )
        time.sleep(3)
        
        client = subprocess.run(
            ['python', 'client/client.py', '--start', '2020-01-01', '--end', '2020-06-30'],
            capture_output=True,
            text=True
        )
        
        end = time.time()
        elapsed = end - start
        
        print(f"Output: {client.stdout.strip()}" + f" (Time: {elapsed:.2f}s)")
        
        results.append({
            'policy': policy,
            'algorithm': algorithm,
            'response': client.stdout.strip(),
            'time': elapsed
        })
        
        server.terminate()
        time.sleep(2)


print("\nResults")
for result in results:
    print(f"policy={result['policy']} algorithm={result['algorithm']} time={result['time']:.2f}s")
from collections import defaultdict

"""
Format: qdrant: {n : (average, max t_q)}, same for retrieval {n : t_r}
ID=15 1 3 1
Real time: 969.57 seconds
CPU time: 1058.55 seconds
"""

n_qdrant_results = defaultdict(list)  # {n : [real time for that n]}
n_ret_results = defaultdict(list)  # {n : [real time for question]}
d_qdrant_results = defaultdict(list)  # {d : [real time for that n]}
d_ret_results = defaultdict(list)  # {d : [real time for question]}

qdrant_report_path = 'qdrant_report.txt'
retrieval_report_path = 'retrieval_report.txt'
 
with open(qdrant_report_path, 'r') as file:
    qdrant_report = file.read()
with open(retrieval_report_path, 'r') as file:
    retrieval_report = file.read()

# PROCESS QDRANT REPORT
qdrant_lines = qdrant_report.splitlines()
for line_no, line in enumerate(qdrant_lines):
    n, d = None, None
    if line_no < 570: #  varying n
        d = 1
        if line.startswith("ID"):
            r_id = line[3:]
            if r_id.startswith("20"):
                n = 20
            elif r_id.startswith("15"):
                n = 15
            elif r_id.startswith("10"):
                n = 10
            elif r_id.startswith("5"):
                n = 5
            elif r_id.startswith("1"):
                n = 1
            else:
                print("uh oh")
        
            real_time_line = qdrant_lines[line_no+1]  # e.g. "Real time: 969.57 seconds"
            real_time = float(real_time_line.split()[2])
            n_qdrant_results[n].append(real_time)

    else: # varying d
        n = 1
        if line.startswith("ID"):
            r_id = line[3:]  # e.g. r_id = 1302 for n = 1, d = 3
            d = int(r_id[1])

            real_time_line = qdrant_lines[line_no+1]  # e.g. "Real time: 969.57 seconds"
            real_time = float(real_time_line.split()[2])
            d_qdrant_results[d].append(real_time)


# PROCESS QDRANT REPORT
ret_lines = retrieval_report.splitlines()
for line_no, line in enumerate(ret_lines):
    n, d = None, None
    if line_no < 290: #  varying n
        d = 1
        if line.startswith("N_URIS"):
            n = int(line.split("=")[-1])
            real_time_line = ret_lines[line_no+1]  # e.g. "Real time: 969.57 seconds"
            real_time = float(real_time_line.split()[2])
            n_ret_results[n].append(real_time)

    else: # varying d
        n = 1
        if line.startswith("N_URIS"):
            r_id = line[3:]  # e.g. r_id = 1302 for n = 1, d = 3
            d_line = ret_lines[line_no+5] # e.g. N=1 D=4 Q=9
            assert d_line.startswith("N=")
            d = int(d_line.split()[1][-1])

            real_time_line = ret_lines[line_no+1]  # e.g. "Real time: 969.57 seconds"
            real_time = float(real_time_line.split()[2])
            d_ret_results[d].append(real_time)

# AVERAGE AND PRINT ETC.
print("\nN QDRANT TIMES:")
print(n_qdrant_results)
print("\nN RETRIEVAL TIMES:")
print(n_ret_results)

print("\nD QDRANT TIMES:")
print(d_qdrant_results)
print("\nD RETRIEVAL TIMES:")
print(d_ret_results)

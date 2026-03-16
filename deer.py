import matplotlib.pyplot as plt
import numpy as np
import math
from scipy.optimize import curve_fit

def read_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        column1 = []
        column2 = []
        column3 = [] 
        column4 = []

        for line in lines:
            # Split the line into two columns
            values = line.strip().split()
            # Append the values to their respective lists
            column1.append((float(values[0])))
            column2.append(float(values[1])-float(values[2]))
            column3.append(float(values[1]))
            column4.append(float(values[2]))

        return column1, column2,column3, column4

# Example usage
file_path = 'nv6_4_4_DEER_tau17750_with black box_rfpi=120_8000counts1.txt'  # Replace with your file path
file_path2 = 'nv6_4_4_DEER_tau17750_with black box_rfpi=120_12000counts1.txt'
file_path3 = 'nv6_4_4_DEER_tau17750_with black box_rfpi=120_16000counts1.txt'
file_path4 = 'nv6_4_4_DEER_tau17750_with black box_rfpi=120_20000counts1.txt'
list1, list2,list3, list4 = read_file(file_path)
list1, list5,list6, list7 = read_file(file_path2)
list1, list8,list9, list10 = read_file(file_path3)
list1, list11,list12, list13 = read_file(file_path4)
# Print the lists

def normalize(listx):
    maxc=max(listx)
    for x in range(len(listx)):
          listx[x]=listx[x]/maxc
normalize(list2)
normalize(list5)
normalize(list8)
normalize(list11)
fig,ax= plt.subplots()

ax.plot(list1,list8,label="16000")
ax.plot(list1,list5,label="12000")
ax.plot(list1,list11,label="20000")

print(list3)
print(list4)
ax.legend()
ax.grid()


  
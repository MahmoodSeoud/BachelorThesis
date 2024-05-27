import matplotlib.pyplot as plt
from datetime import datetime

# Your data
timestamps_elves = [
    "12:38:16",
    "12:41:25",
    "12:44:28",
    "12:51:42",
    "12:54:42",
    "12:57:44",
    "13:10:45",
    "13:13:57",
    "13:17:08",
    "13:40:23",
    "13:43:34"
]

runs_elves = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# Convert the timestamps to datetime and calculate the time elapsed since the first timestamp
timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]

# Create a figure and a subplot
fig, ax1 = plt.subplots()

# Plot the data points on the subplot and connect them with a line
ax1.plot(timestamps_elves, runs_elves, '-o', color='orange')

# Set the title and x label
ax1.set_title('Number of runs over time')
ax1.set_xlabel('Time elapsed (minutes)')

# Show the plot
plt.show()
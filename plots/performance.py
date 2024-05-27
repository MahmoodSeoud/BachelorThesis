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

timestamps_reindeer = [
    "16:21:30",
    "16:33:48",
    "16:45:55",
    "16:57:58",
    "17:10:01",
    "17:22:14",
    "17:34:20",
    "17:46:29",
    "17:58:35",
    "18:10:45",
    "18:22:46",
]

runs = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# Convert the timestamps to datetime and calculate the time elapsed since the first timestamp
timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]

# Create a figure and a subplot
fig, ax1 = plt.subplots()

# Plot the data points on the subplot and connect them with a line
ax1.plot(timestamps_elves, runs, '-o', color='green')
ax1.plot(timestamps_reindeer, runs, '-o', color='brown')

# Set the title and x label
ax1.set_title('Number of runs over time')
ax1.set_xlabel('Time elapsed (minutes)')

# Show the plot
plt.show()
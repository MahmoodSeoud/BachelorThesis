import matplotlib.pyplot as plt
from datetime import datetime

# Your data
timestamps_elves = [
"21:37:21",
"21:38:31",
"21:39:34",
"21:40:37",
"21:41:40",
"21:42:43",
"21:43:45",
"21:44:48",
"21:45:51",
"21:55:26",
"21:56:29",
]

timestamps_reindeer = [
"09:08:41",
"09:12:19",
"09:15:47",
"09:19:18",
"09:32:09",
"09:35:39",
"09:52:23",
"09:55:50",
"09:59:14",
"10:02:42",
"10:06:12",
]

runs = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# Convert the timestamps to datetime and calculate the time elapsed since the first timestamp
timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]
timestamps_reindeer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_reindeer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_reindeer]

# Create a figure and a subplot
fig, ax1 = plt.subplots()

# Plot the data points on the subplot and connect them with a line
ax1.plot(timestamps_elves, runs, '-o', color='green')
ax1.plot(timestamps_reindeer, runs, '-o', color='brown')

# Set the title and x label
ax1.set_title('Number of runs over time')
ax1.set_xlabel('Time elapsed (minutes)')
ax1.set_ylabel('Number of runs')
ax1.legend(['Elves', 'Reindeer'])

# Show the plot
plt.show()

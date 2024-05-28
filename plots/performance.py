import matplotlib.pyplot as plt
from datetime import datetime

# Your data
timestamps_elves = [
"16:53:19",
"16:54:27",
"16:55:29",
"16:56:31",
"16:57:32",
"16:58:34",
"16:59:36",
"17:00:37",
"17:01:40",
"17:02:41",
"17:03:41",
]

timestamps_reindeer = [
"15:04:07",
"15:05:07",
"15:06:04",
"15:06:58",
"15:07:52",
"15:08:54",
"15:09:48",
"15:10:44",
"15:11:38",
"15:12:33",
"15:13:28",
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

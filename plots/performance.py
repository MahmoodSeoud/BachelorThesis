import matplotlib.pyplot as plt
from datetime import datetime

# Your data
timestamps_elves = [
"15:19:23",
"15:20:27",
"15:21:27",
"15:22:27",
"15:23:28",
"15:24:30",
"15:39:30",
"15:40:35",
"15:41:39",
"15:42:42",
"15:43:46",
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

timestamps_non_distributed = [
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
"17:53:16",
]

timestamps_distributed = [
"19:21:17",
"19:21:55",
"19:22:24",
"19:22:53",
"19:23:22",
"19:23:52",
"19:24:26",
"19:25:08",
"19:25:37",
"19:26:06",
"19:26:48",
]

runs = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# Convert the timestamps to datetime and calculate the time elapsed since the first timestamp
#timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]
#timestamps_reindeer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_reindeer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_reindeer]

timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]
timestamps_reindeer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_reindeer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_reindeer]

# Create a figure and a subplot
fig, ax1 = plt.subplots()

# Plot the data points on the subplot and connect them with a line
#ax1.plot(timestamps_elves, runs, '-o', color='green')
#ax1.plot(timestamps_reindeer, runs, '-o', color='brown')

ax1.plot(timestamps_elves, runs, '-o', color='red')
ax1.plot(timestamps_reindeer, runs, '-o', color='blue')

# Set the title and x label
ax1.set_title('Number of runs over time')
ax1.set_xlabel('Time elapsed (minutes)')
ax1.set_ylabel('Number of runs')
ax1.legend(['Elves', 'Reindeer'])

# Show the plot
plt.show()

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
"18:02:49",
"18:03:29",
"18:03:59",
"18:04:28",
"18:04:58",
"18:05:27",
"18:05:57",
"18:06:27",
"18:06:57",
"18:07:27",
"18:07:57",
]

runs = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# Convert the timestamps to datetime and calculate the time elapsed since the first timestamp
#timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]
#timestamps_reindeer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_reindeer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_reindeer]

timestamps_non_distributed = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_non_distributed[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_non_distributed]
timestamps_distributed = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(timestamps_distributed[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_distributed]

# Create a figure and a subplot
fig, ax1 = plt.subplots()

# Plot the data points on the subplot and connect them with a line
#ax1.plot(timestamps_elves, runs, '-o', color='green')
#ax1.plot(timestamps_reindeer, runs, '-o', color='brown')

ax1.plot(timestamps_non_distributed, runs, '-o', color='red')
ax1.plot(timestamps_distributed, runs, '-o', color='blue')

# Set the title and x label
ax1.set_title('Number of runs over time')
ax1.set_xlabel('Time elapsed (minutes)')
ax1.set_ylabel('Number of runs')
ax1.legend(['Elves', 'Reindeer'])

# Show the plot
plt.show()

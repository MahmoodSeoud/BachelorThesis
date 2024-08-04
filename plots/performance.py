import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

# Your data
timestamps_elves = [
    "10:25:53",
    "10:27:00",
    "10:28:02",
    "10:29:03",
    "10:30:05",
    "10:31:07",
    "10:32:09",
    "10:33:11",
    "10:34:13",
    "10:35:14",
    "10:36:15",
]

timestamps_nukedElves = [
    "09:50:44",
    "09:52:31",
    "09:53:33",
    "09:54:34",
    "09:55:37",
    "09:56:39",
    "09:58:34",
    "09:59:35",
    "10:00:37",
    "10:01:39",
    "10:02:41"
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
    "15:13:28",]

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

timestamps_distributedThreadingTCPServer = [
    "17:30:32",
    "17:31:10",
    "17:31:40",
    "17:32:15",
    "17:33:13",
    "17:33:57",
    "17:34:35",
    "17:35:21",
    "17:35:52",
    "17:36:34",
    "17:37:06",
]


timestamps_distributedTCPServer = [
    "15:58:49",
    "15:59:26",
    "15:59:56",
    "16:00:25",
    "16:00:55",
    "16:01:24",
    "16:02:59",
    "16:04:03",
    "16:05:06",
    "16:06:11",
    "16:07:17",

]

runs = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# Convert the timestamps to datetime and calculate the time elapsed since the first timestamp
timestamps_elves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(
    timestamps_elves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_elves]
timestamps_reindeer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(
    timestamps_reindeer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_reindeer]
timestamps_nukedElves = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(
    timestamps_nukedElves[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_nukedElves]

timestamps_non_distributed = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(
    timestamps_non_distributed[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_non_distributed]
timestamps_distributedThreadingTCPServer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(
    timestamps_distributedThreadingTCPServer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_distributedThreadingTCPServer]
timestamps_distributedTCPServer = [(datetime.strptime(time, "%H:%M:%S") - datetime.strptime(
    timestamps_distributedTCPServer[0], "%H:%M:%S")).seconds / 60.0 for time in timestamps_distributedTCPServer]


# Create a figure and a subplot
fig, ax = plt.subplots(figsize=(10, 5))


x1 = timestamps_elves
x2 = timestamps_nukedElves
y = runs
x1label = "Elves"
x2label = "(n/2) + 1 Elves"

# Plot the data points on the subplot and connect them with a line
# ax1.plot(timestamps_elves, runs, '-o', color='orange')
# ax1.plot(timestamps_nukedElves, runs, '-o', color='red')
# ax1.plot(timestamps_reindeer, runs, '-o', color='brown')

# Set the title and x label

# Define font sizes
SIZE_DEFAULT = 14
SIZE_LARGE = 16
plt.rc("font", family="Arial")  # controls default font
plt.rc("font", weight="normal")  # controls default font
plt.rc("font", size=SIZE_DEFAULT)  # controls default text sizes
plt.rc("axes", titlesize=SIZE_LARGE)  # fontsize of the axes title
plt.rc("axes", labelsize=SIZE_LARGE)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=SIZE_DEFAULT)  # fontsize of the tick labels
plt.rc("ytick", labelsize=SIZE_DEFAULT)  # fontsize of the tick labels

# Hide the all BUT the bottom spines (axis lines)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)
ax.spines["top"].set_visible(False)

# Only show ticks on the left and bottom spines
ax.yaxis.set_ticks_position("left")
ax.xaxis.set_ticks_position("bottom")
ax.spines["bottom"].set_bounds(min(x2), max(x2) + 1)


ax.plot(x1,
        y,
        color="darkred",
        linewidth=2,
        label=x1label)

ax.plot(x2,
        y,
        color="darkorange",
        linewidth=2,
        label=x2label)

ax.set_xticks(np.arange(min(x2), max(x2) + 1))
ax.set_xlabel('Time (minutes)', fontsize=16)  # Adjust the fontsize as needed
ax.set_ylabel('Runs', fontsize=16)  # Adjust the fontsize as needed

ax.legend()

plt.savefig("Elves_vs_nukedElves.png", dpi=300)
# Show the plot
plt.show()

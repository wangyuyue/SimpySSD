def total(time, value):
    total = 0
    for i, t in enumerate(time):
        if i < len(time) - 1:
            total += value[i] * (time[i+1] - time[i])
    return total

def smooth_timeline(time, value, unit):
    cur = time[0] - time[0] % unit
    ti = 0
    smooth_time = [cur]
    smooth_value = [0]
    
    while cur < time[-1]:
        if time[ti] < smooth_time[-1] + unit:
            if ti > 0:
                smooth_value[-1] += value[ti-1] * (time[ti] - cur)
            cur = time[ti]
            ti += 1
        else:
            if ti > 0:
                smooth_value[-1] += value[ti-1] * (smooth_time[-1] + unit - cur)
            cur = smooth_time[-1] + unit
            smooth_time.append(cur)
            smooth_value.append(0)

    smooth_value = [value/unit for value in smooth_value]

    return smooth_time, smooth_value

def average_timeline(timeseries):
    times = []
    for time, _ in timeseries:
        times.extend(time)
    times = sorted(set(times))
    new_values = []
    for time, value in timeseries:
        new_value = [0]
        i = 0
        for t in times:
            if t < time[i]:
                new_value.append(new_value[-1])
            else:
                new_value.append(value[i])
                if i < len(time) - 1:
                    i += 1
        new_value.pop(0)
        new_values.append(new_value)
    avg_value = [sum(tup)/len(tup) for tup in zip(*new_values)]
    return times, avg_value
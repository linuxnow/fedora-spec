The repo related to these packages can be found here:

Before Fedora 35:
https://copr.fedorainfracloud.org/coprs/ycollet/linuxmao/

After (including) Fedora 35:
https://copr.fedorainfracloud.org/coprs/ycollet/audinux/

This repo has old packages for Fedora 25 to 40 and up to date packages for Fedora 43, 44 and rawhide.

To install a package from the COPR repository:
```
$ sudo dnf copr enable ycollet/audinux
$ sudo dnf install <package_name>
```

Install the rpm file using yum:
as a root user:
```
$ yum install filename.rpm
# or
$ dnf install filename.rpm
```

To mirror the COPR repository:
```
$ mkdir -p rpm-copr/44
$ cd rpm-copr/44
$ dnf reposync --release=44 --repoid=copr:copr.fedorainfracloud.org:ycollet:audinux --destdir . --downloadcomp
```

To build the packages yourself, see [BUILDING.md](BUILDING.md).

# Caveats

Known issues encountered on real-time audio workstations and their solutions.

## Scheduled system tasks causing GPU freeze and Wayland hang

**Symptom:** The NVIDIA GPU freezes briefly, KWin/Wayland hangs, and the
journal shows:

```
kernel: nvidia-modeset: ERROR: GPU:0: Idling display engine timed out: 0x0000987d:0:0:1255
kwin_wayland: The main thread was hanging temporarily!
systemd[1]: Starting plocate-updatedb.service - Update the plocate database...
```

All three lines appear at exactly the same timestamp.

**Root cause:** Fedora installs several scheduled maintenance timers
(`plocate-updatedb`, `dnf-makecache`, `fwupd-refresh`, `man-db-cache-update`,
etc.) that run automatically in the background. These tasks perform heavy
filesystem or network I/O without any RT awareness. The resulting burst of I/O
saturates the memory bus and PCIe bandwidth, causing the NVIDIA driver's
internal DMA/command queue operations to stall past their timeout. The Wayland
compositor hangs because it cannot communicate with the GPU during that window.

This is not specific to NVIDIA — any GPU driver with internal timeouts can be
affected. It is also a common source of audio xruns even when no GPU freeze is
visible.

**Fix — disable the offending timer:**

```bash
sudo systemctl disable --now plocate-updatedb.timer
```

You can still rebuild the locate database manually when needed:

```bash
sudo updatedb
```

**Alternative — keep the timer but lower its priority:**

```bash
sudo systemctl edit plocate-updatedb.service
```

Add the following and save:

```ini
[Service]
Nice=19
IOSchedulingClass=idle
IOSchedulingPriority=7
CPUSchedulingPolicy=idle
```

This instructs the kernel to give `updatedb` the lowest possible CPU and I/O
priority so it yields immediately whenever anything else needs the bus.

**Check for other disruptive timers:**

```bash
systemctl list-timers --all
```

The table below lists the Fedora maintenance services most likely to cause
xruns or GPU freezes on an RT audio workstation, and the recommended action
for each.

| Service | Why it hurts | Recommendation |
|---|---|---|
| `plocate-updatedb` | Full filesystem scan — saturates I/O bus | Disable or idle-nice |
| `dnf-makecache` | DNF metadata refresh — network + disk bursts | Idle-nice or disable |
| `fwupd-refresh` | Firmware update DB sync — network + disk | Idle-nice or disable |
| `man-db-cache-update` | man page DB rebuild — filesystem scan | Idle-nice or disable |
| `logrotate` | Log compression — CPU + I/O spike | Idle-nice |
| `systemd-journal-flush` | Journal flush to disk — I/O spike on rotation | Idle-nice |

To lower priority for any of the above, run `sudo systemctl edit <name>.service`
and add:

```ini
[Service]
Nice=19
IOSchedulingClass=idle
IOSchedulingPriority=7
CPUSchedulingPolicy=idle
```

To disable a timer entirely (and run it manually when needed):

```bash
sudo systemctl disable --now <name>.timer
```

# Star History

[![Star History Chart](https://api.star-history.com/svg?repos=audinux/fedora-spec&type=Date)](https://star-history.com/#audinux/fedora-spec&Date)

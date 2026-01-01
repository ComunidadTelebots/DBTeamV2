"""Owner-only CPU "top"-like command plugin.

Registers command `/top` which reports CPU, memory and top processes.
Requires `psutil` to be installed; otherwise suggests installation.
Only users with role `owner` (via `storage.get_role`) may run this command.
"""
import asyncio
import html
from typing import Any

from python_bot.storage import storage


def setup(bot):
    bot.register_command('top', top_cmd, 'Owner-only: show CPU/memory/processes (like top)', plugin='cpu_top')


async def top_cmd(update: Any, context: Any):
    user = update.effective_user
    if not user:
        return
    role = storage.get_role(user.id)
    if role != 'owner':
        await update.message.reply_text('Permission denied: owner only')
        return

    loop = asyncio.get_running_loop()
    try:
        out = await loop.run_in_executor(None, _gather_stats)
    except Exception as e:
        await update.message.reply_text(f'Failed to gather stats: {e}')
        return

    # send as preformatted HTML to avoid markdown escaping issues
    await update.message.reply_text(f"<pre>{html.escape(out)}</pre>", parse_mode='HTML')


def _gather_stats() -> str:
    try:
        import psutil
    except Exception:
        return 'psutil not installed. Install with: pip install psutil'

    def _hbytes(n: int) -> str:
        # human-readable bytes
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024.0:
                return f"{n:.1f}{unit}"
            n /= 1024.0
        return f"{n:.1f}PB"

    lines = []
    try:
        cpu = psutil.cpu_percent(interval=1)
        per = psutil.cpu_percent(interval=0.1, percpu=True)
        vm = psutil.virtual_memory()
        lines.append(f"CPU: {cpu:.1f}%")
        lines.append('Per-CPU: ' + ', '.join(f"{p:.1f}%" for p in per))
        lines.append(f"Memory: {vm.percent:.1f}% ({_hbytes(vm.used)}/{_hbytes(vm.total)})")

        procs = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                cpu_p = p.cpu_percent(interval=0.0)
                mem_p = p.memory_percent()
                procs.append((cpu_p, mem_p, p.pid, p.info.get('name') or ''))
            except Exception:
                continue

        procs.sort(key=lambda x: x[0], reverse=True)
        lines.append('\nTop processes by CPU:')
        lines.append(f"{'PID':>6} {'CPU%':>6} {'MEM%':>6} NAME")
        for cpu_p, mem_p, pid, name in procs[:8]:
            lines.append(f"{pid:6d} {cpu_p:6.1f} {mem_p:6.1f} {name}")

    except Exception as e:
        lines.append(f"Error gathering stats: {e}")

    return '\n'.join(lines)

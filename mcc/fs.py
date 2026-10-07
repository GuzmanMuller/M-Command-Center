"""POSIX descriptor-bound roots and bounded no-follow reads."""
import os
import stat
from pathlib import Path

def canonical(path):
    path=Path(path).expanduser().absolute()
    if ".." in path.parts:
        raise ValueError("Root traversal is prohibited")
    for p in [path,*path.parents]:
        if p.is_symlink():
            raise ValueError("Root symlink aliases are prohibited")
    return path

def check_directory(fd,private=False):
    info=os.fstat(fd)
    mode=stat.S_IMODE(info.st_mode)
    if info.st_uid not in (0,os.getuid()):
        raise ValueError("Untrusted ancestor owner")
    if mode & 0o022 and not (mode & stat.S_ISVTX and info.st_uid==0):
        raise ValueError("Writable untrusted ancestry")
    if private and (info.st_uid!=os.getuid() or mode&0o077):
        raise ValueError("Root must be owner-controlled mode 0700")

def open_root(path,create=False):
    path=Path(path).expanduser().absolute()
    if ".." in path.parts:raise ValueError("Root traversal prohibited")
    current=os.open("/",os.O_RDONLY|os.O_DIRECTORY)
    try:
        check_directory(current)
        for index,part in enumerate(path.parts[1:]):
            final=index==len(path.parts[1:])-1
            try:
                following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
                if create and final:
                    os.close(following);raise FileExistsError("Root already exists")
            except FileNotFoundError:
                if not create:raise
                os.mkdir(part,0o700,dir_fd=current)
                following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
            os.close(current);current=following
            check_directory(current,private=final)
        return current
    except BaseException:
        os.close(current);raise

def root_fd(path):
    return open_root(path)

def initialize(path):
    return open_root(path,create=True)

def read_at(fd,name,limit,private=True):
    rel=Path(name)
    if rel.is_absolute() or not rel.parts or any(x in ("..", ".") for x in rel.parts):
        raise ValueError("Invalid relative selection")
    current=os.dup(fd)
    try:
        for part in rel.parts[:-1]:
            following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
            os.close(current);current=following
        leaf=os.open(rel.parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=current)
        try:
            info=os.fstat(leaf)
            if not stat.S_ISREG(info.st_mode) or info.st_size>limit:
                raise ValueError("Expected bounded regular file")
            if private and (info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077):
                raise ValueError("File must be owner-controlled mode 0600")
            with os.fdopen(leaf,"rb",closefd=False) as stream:
                value=stream.read(limit+1)
            if len(value)>limit:raise ValueError("File exceeds limit")
            return value
        finally:os.close(leaf)
    finally:os.close(current)

def write_at(fd,name,value):
    temporary=name+".next"
    leaf=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        with os.fdopen(leaf,"w",encoding="utf-8") as f:
            f.write(value);f.flush();os.fsync(f.fileno())
        os.replace(temporary,name,src_dir_fd=fd,dst_dir_fd=fd)
        os.fsync(fd)
    except BaseException:
        try:os.unlink(temporary,dir_fd=fd)
        except OSError:pass
        raise

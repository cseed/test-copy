import sys
import secrets
import os.path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from hailtop.batch_client.parse import parse_memory_in_bytes
from hailtop.aiotools.fs import RouterAsyncFS, LocalAsyncFS
from hailtop.aiogoogle import GoogleStorageAsyncFS
from hailtop.aiotools.s3asyncfs import S3AsyncFS

KiB = 1024
MiB = 1024 * KiB
GiB = 1024 * MiB


async def create_test_file(fs, sema, dest_base, file_size, depth):
    async with sema:
        token = secrets.token_hex(16)

        path = dest_base
        for i in range(depth):
            path = os.path.join(path, token[i])
        await fs.makedirs(path, exist_ok=True)

        path = os.path.join(path, token)

        # print(f'writing {path}')

        async with await fs.create(path) as out:
            while file_size > 0:
                b = secrets.token_bytes(min(file_size, 10 * MiB))
                await out.write(b)
                file_size -= len(b)


async def create_test_data(fs, sema, dest_base, total_size, n_files, depth):
    await asyncio.gather(*[
        create_test_file(fs, sema, dest_base, total_size // n_files, depth)
        for _ in range(n_files)
    ])


async def main():
    config = json.loads(sys.argv[1])
    total_size = parse_memory_in_bytes(config['size'])
    n_files = config['n-files']
    depth = config['depth']
    data_dest_base = sys.argv[2]

    with ThreadPoolExecutor() as thread_pool:
        async with RouterAsyncFS('file', [LocalAsyncFS(thread_pool),
                                          GoogleStorageAsyncFS(),
                                          S3AsyncFS(thread_pool)]) as fs:
            sema = asyncio.Semaphore(15)
            await create_test_data(fs, sema, data_dest_base, total_size, n_files, depth),


if __name__ == '__main__':
    asyncio.run(main())

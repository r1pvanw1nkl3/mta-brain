import io
import zipfile
import logging
import contextlib
from . import db_loader

logger = logging.getLogger(__name__)

def process_gtfs_zip(pool, zip_file_path: str, schema: str = "public"):
    """
    Parses and loads the GTFS zip into the db.
    """
    logger.info(f"Loading {zip_file_path} into schema {schema}")

    with zipfile.ZipFile(zip_file_path, 'r') as zip:
        with contextlib.ExitStack() as stack:
            data_map = {}
            for filename in zip.namelist():
                if filename.endswith('.txt'):
                    table_name = filename[:-4]
                    bin_file = stack.enter_context(zip.open(filename))
                    txt_file = stack.enter_context(io.TextIOWrapper(bin_file, encoding='utf-8'))
                    data_map[table_name] = txt_file

            try:
                with pool.connection() as conn:
                    db_loader.load_all(conn, data_map, schema)
                logger.info("Successfully proccessed the GTFS feed.")
            except Exception as e:
                logger.error(f"An error occurred when processing GTFS feed: {e}")
                raise
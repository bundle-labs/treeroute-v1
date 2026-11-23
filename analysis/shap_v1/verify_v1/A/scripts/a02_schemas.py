# Round 14, implementer A: print parquet schemas (names and types) and row counts only.
import sys
import pyarrow.parquet as pq


def main():
    for path in sys.argv[1:]:
        pf = pq.ParquetFile(path)
        sch = pf.schema_arrow
        print("==", path.replace("\\", "/").split("/")[-4:], "rows", pf.metadata.num_rows, "cols", len(sch.names))
        names = sch.names
        if len(names) > 80:
            print("  first 40:", [(n, str(sch.field(n).type)) for n in names[:40]])
            print("  ... last 10:", [(n, str(sch.field(n).type)) for n in names[-10:]])
        else:
            print("  ", [(n, str(sch.field(n).type)) for n in names])


if __name__ == "__main__":
    main()

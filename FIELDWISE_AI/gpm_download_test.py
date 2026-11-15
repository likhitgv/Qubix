
import earthaccess
import os

print("Logging in to NASA Earthdata...")

auth = earthaccess.login(strategy="interactive")

if auth:
    print("Login successful!")

    os.makedirs("data/gpm/test", exist_ok=True)

    results = earthaccess.search_data(
        short_name="GPM_3IMERGDF",
        version="07",
        temporal=("2025-01-01", "2025-01-01")
    )

    print("Granules found:", len(results))

    if results:
        files = earthaccess.download(
            results[:1],
            local_path="data/gpm/test"
        )
        print("Downloaded:", files)
else:
    print("Login failed!")

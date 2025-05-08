#!/usr/bin/env python3
import argparse, concurrent.futures, json, os, random, string, subprocess, time

# === original snippet kept verbatim ===
original_bash = r'''#!/usr/bin/env bash

# ensure Route 53 Domains uses the correct endpoint
export AWS_DEFAULT_REGION=us-east-1

# Fill in contact details
ADMIN_CONTACT='{
  "FirstName": "ur",
  "LastName": "mom",
  "ContactType": "PERSON",
  "OrganizationName": "",
  "AddressLine1": "350 bush st",
  "AddressLine2": "",
  "City": "sf",
  "State": "CA",
  "CountryCode": "US",
  "ZipCode": "42123",
  "PhoneNumber": "+1.1231231234",
  "Email": "erosolar@twitch.tv"
}'

REGISTRANT_CONTACT="$ADMIN_CONTACT"
TECH_CONTACT="$ADMIN_CONTACT"

aws route53domains register-domain \
  --region us-east-1 \
  --domain-name erosolar.tv \
  --duration-in-years 10 \
  --auto-renew \
  --privacy-protect-admin-contact \
  --privacy-protect-registrant-contact \
  --privacy-protect-tech-contact \
  --admin-contact "$ADMIN_CONTACT" \
  --registrant-contact "$REGISTRANT_CONTACT" \
  --tech-contact "$TECH_CONTACT"
'''

# === python implementation ===
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

ADMIN_CONTACT = {
    "FirstName": "ur",
    "LastName": "mom",
    "ContactType": "PERSON",
    "OrganizationName": "",
    "AddressLine1": "350 bush st",
    "AddressLine2": "",
    "City": "sf",
    "State": "CA",
    "CountryCode": "US",
    "ZipCode": "42123",
    "PhoneNumber": "+1.1231231234",
    "Email": "erosolar@twitch.tv",
}
ADMIN_JSON = json.dumps(ADMIN_CONTACT)

def gen_domain() -> str:
    root = random.choice(
        ["erosolar", "er0solar", "eros0lar", "erosolr", "er0solr"]
    ) + "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
    return f"{root}.tv"

def register(domain: str) -> tuple[bool, str]:
    cmd = [
        "aws",
        "route53domains",
        "register-domain",
        "--region",
        "us-east-1",
        "--domain-name",
        domain,
        "--duration-in-years",
        "10",
        "--auto-renew",
        "--privacy-protect-admin-contact",
        "--privacy-protect-registrant-contact",
        "--privacy-protect-tech-contact",
        "--admin-contact",
        ADMIN_JSON,
        "--registrant-contact",
        ADMIN_JSON,
        "--tech-contact",
        ADMIN_JSON,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        try:
            oid = json.loads(res.stdout)["OperationId"]
        except Exception:
            oid = ""
        return True, oid
    return False, res.stderr.strip()

def worker(seed: str | None = None) -> None:
    time.sleep(random.randint(12, 36))
    while True:
        dom = seed or gen_domain()
        ok, _ = register(dom)
        if ok:
            time.sleep(random.randint(60, 108))
            break
        if seed:
            break

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", help="domain to register")
    args = parser.parse_args()

    max_workers = 9
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for i in range(max_workers):
            ex.submit(worker, args.seed if i == 0 else None)
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()
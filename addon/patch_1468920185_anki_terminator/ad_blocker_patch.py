import importlib
from urllib.parse import urlparse
from aqt import mw
from aqt.qt import *
from ..logger import companion_logger

def get_url_domains(url):
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return []
        hostname = hostname.lower()
        parts = hostname.split('.')
        suffixes = []
        for i in range(len(parts)):
            suffixes.append('.'.join(parts[i:]))
        return suffixes
    except Exception:
        return []

def match_rules(url, pure_domains_set, path_rules_list):
    url_domains = get_url_domains(url)
    for dom in url_domains:
        if dom in pure_domains_set:
            return True
    if any(rule in url for rule in path_rules_list):
        return True
    return False

def patch(ad_blocker_mod):
    # Check if adblocker optimization is enabled
    config = mw.addonManager.getConfig("000_addon_fixes") or {}
    if not config.get("enable_adblocker_optimization", True):
        companion_logger.log("Ad-Blocker optimization is disabled in settings, skipping.")
        return

    # 1. Redefine load_ad_domains_from_easylist
    def optimized_load_ad_domains(path=ad_blocker_mod.easylist_path):
        companion_logger.log("Optimizing ad-blocker rule matching loading...")
        block_domains = set()
        allow_domains = set()

        with open(path, encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("!"):
                    continue

                if line.startswith("@@||"):
                    raw_rule = line[4:].split("$")[0]
                    domain = raw_rule.split("^")[0]
                    if domain:
                        allow_domains.add(domain)
                elif line.startswith("||"):
                    raw_rule = line[2:].split("$")[0]
                    domain = raw_rule.split("^")[0]
                    if domain:
                        block_domains.add(domain)

        # extra
        for domain in ad_blocker_mod.extra_block_domain_list:
            block_domains.add(domain)
        for domain in ad_blocker_mod.extra_allow_domain_list:
            allow_domains.add(domain)

        # Separate pure domains (no path) and path rules
        block_pure_domains = set()
        block_path_rules = []
        for d in block_domains:
            if "/" in d:
                block_path_rules.append(d)
            else:
                block_pure_domains.add(d)

        allow_pure_domains = set()
        allow_path_rules = []
        for d in allow_domains:
            if "/" in d:
                allow_path_rules.append(d)
            else:
                allow_pure_domains.add(d)

        companion_logger.log(f"Ad-blocker optimization complete: split {len(block_domains)} block domains into {len(block_pure_domains)} pure set entries.")
        return block_pure_domains, block_path_rules, allow_pure_domains, allow_path_rules

    # Apply patched load function
    ad_blocker_mod.load_ad_domains_from_easylist = optimized_load_ad_domains

    # 2. Redefine AdBlocker class properties and matching logic
    AdBlockerClass = ad_blocker_mod.AdBlocker
    
    # Reload properties with optimized split
    (AdBlockerClass.block_pure_domains, 
     AdBlockerClass.block_path_rules, 
     AdBlockerClass.allow_pure_domains, 
     AdBlockerClass.allow_path_rules) = optimized_load_ad_domains()

    # Redefine interceptRequest
    def optimized_intercept_request(self, info: QWebEngineUrlRequestInfo):
        try:
            url = info.requestUrl().toString()
            first_party_url = info.firstPartyUrl().toString()

            # disable website list
            if any(site in first_party_url for site in ad_blocker_mod.disabled_on_sites):
                return

            # white list
            if match_rules(url, self.allow_pure_domains, self.allow_path_rules):
                return

            if self.adblock_engine:
                resource_type = ad_blocker_mod.QT_RESOURCE_TYPES.get(info.resourceType(), "other")
                result = self.adblock_engine.check_network_urls(
                    url=url,
                    source_url=first_party_url,
                    request_type=resource_type
                )
                if result.matched:
                    info.block(True)
            else:
                # block list
                if match_rules(url, self.block_pure_domains, self.block_path_rules):
                    info.block(True)

        except Exception as e:
            companion_logger.log(f"Error in optimized interceptRequest: {e}")

    AdBlockerClass.interceptRequest = optimized_intercept_request
    companion_logger.log("Successfully hooked AdBlocker interceptRequest with O(1) set matching.")

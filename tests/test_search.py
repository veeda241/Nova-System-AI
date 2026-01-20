#!/usr/bin/env python3
"""Quick test for search functionality"""
import webbrowser
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_search(user_input):
    lower_input = user_input.lower().strip()
    
    # Pattern 1: google search, search google, search for, google
    prefixes = ['google search ', 'search google ', 'search for ', 'google ']
    if any(lower_input.startswith(p) for p in prefixes):
        query = lower_input
        for prefix in prefixes:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        if query:
            print(f"🔍 Searching Google for '{query}'...")
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            print(f"✅ Google search opened")
            return True
    
    # Pattern 2: search X (generic)
    if lower_input.startswith('search ') and not any(x in lower_input for x in ['files', 'youtube', 'file', 'folder']):
        query = lower_input.replace('search ', '').strip()
        if query and len(query) > 1:
            print(f"🔍 Searching Google for '{query}'...")
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            print(f"✅ Google search completed")
            return True
    
    print(f"❌ No search pattern matched for: {user_input}")
    return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_search(' '.join(sys.argv[1:]))
    else:
        # Test cases
        test_search("search for a2d")

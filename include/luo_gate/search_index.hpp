#pragma once

#include <algorithm>
#include <cctype>
#include <map>
#include <set>
#include <string>
#include <string_view>
#include <vector>

namespace luo_gate {

// Simple token-based inverted index for fast cross-store search.
// Documents are added with a kind+id key; search returns matching keys ranked by hit count.

struct SearchDoc {
    std::string kind;   // "task" | "file" | "memory" | "knowledge" | "agent" | "log"
    std::string id;
    std::string title;
    std::string body;   // searchable text
};

struct SearchHit {
    std::string kind;
    std::string id;
    std::string title;
    std::string excerpt;
    int         hits = 0;
};

class SearchIndex {
public:
    void clear() { posting_.clear(); docs_.clear(); }

    void add(SearchDoc doc) {
        const auto key = doc.kind + ":" + doc.id;
        docs_[key] = doc;
        for (const auto& tok : tokenize(doc.title + " " + doc.body))
            posting_[tok].insert(key);
    }

    void remove(const std::string& kind, const std::string& id) {
        const auto key = kind + ":" + id;
        docs_.erase(key);
        for (auto& [tok, keys] : posting_) keys.erase(key);
    }

    std::vector<SearchHit> search(std::string_view query, std::size_t limit = 30) const {
        const auto tokens = tokenize(query);
        if (tokens.empty()) return {};

        std::map<std::string, int> scores;
        for (const auto& tok : tokens) {
            // Exact match
            auto it = posting_.find(tok);
            if (it != posting_.end())
                for (const auto& key : it->second) scores[key]++;
            // Prefix match (for partial queries)
            for (const auto& [index_tok, keys] : posting_) {
                if (index_tok.size() >= tok.size() &&
                    index_tok.substr(0, tok.size()) == tok)
                    for (const auto& key : keys)
                        if (scores.find(key) == scores.end() || scores[key] < 1)
                            scores[key] += 1;
            }
        }

        // Collect and rank
        std::vector<SearchHit> results;
        for (const auto& [key, score] : scores) {
            auto dit = docs_.find(key);
            if (dit == docs_.end()) continue;
            const auto& doc = dit->second;
            SearchHit hit;
            hit.kind = doc.kind;
            hit.id = doc.id;
            hit.title = doc.title;
            hit.hits = score;
            // Extract excerpt around first query token match
            const auto& body = doc.body;
            std::size_t pos = std::string::npos;
            for (const auto& tok : tokens) {
                auto p = body.find(tok);
                if (p != std::string::npos) { pos = p; break; }
            }
            if (pos != std::string::npos) {
                const auto start = pos > 40 ? pos - 40 : 0;
                hit.excerpt = body.substr(start, 120);
            } else {
                hit.excerpt = body.substr(0, 80);
            }
            results.push_back(hit);
        }

        std::sort(results.begin(), results.end(),
                  [](const SearchHit& a, const SearchHit& b){ return a.hits > b.hits; });
        if (results.size() > limit) results.resize(limit);
        return results;
    }

    std::size_t doc_count() const { return docs_.size(); }

private:
    static std::vector<std::string> tokenize(std::string_view text) {
        std::vector<std::string> tokens;
        std::string tok;
        for (unsigned char c : text) {
            if (std::isalnum(c) || c == '_' || c == '-') {
                tok += static_cast<char>(std::tolower(c));
            } else if (!tok.empty()) {
                if (tok.size() >= 2) tokens.push_back(tok);
                tok.clear();
            }
        }
        if (tok.size() >= 2) tokens.push_back(tok);
        // Deduplicate
        std::sort(tokens.begin(), tokens.end());
        tokens.erase(std::unique(tokens.begin(), tokens.end()), tokens.end());
        return tokens;
    }

    std::map<std::string, std::set<std::string>> posting_; // token -> doc keys
    std::map<std::string, SearchDoc>             docs_;
};

} // namespace luo_gate

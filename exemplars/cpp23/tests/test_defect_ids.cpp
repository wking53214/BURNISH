// The C++23 exemplar against the shared vectors in exemplars/vectors.txt.
// Usage: test_defect_ids PATH_TO_VECTORS

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "defect_ids.hpp"

namespace {

using Row = std::vector<std::string>;

int failures = 0;

void expect(bool condition, const std::string& what) {
    if (!condition) {
        std::cerr << "FAIL: " << what << '\n';
        ++failures;
    }
}

std::vector<Row> read_rows(const std::string& path, const std::string& kind) {
    std::ifstream in(path);
    if (!in) {
        std::cerr << "cannot read vectors file " << path << '\n';
        std::exit(2);
    }
    std::vector<Row> rows;
    for (std::string line; std::getline(in, line);) {
        if (line.starts_with('#')) {
            continue;
        }
        std::istringstream words(line);
        Row row;
        for (std::string word; words >> word;) {
            row.push_back(word == "<empty>" ? std::string{} : word);
        }
        if (!row.empty() && row.front() == kind) {
            rows.emplace_back(row.begin() + 1, row.end());
        }
    }
    return rows;
}

std::vector<std::string> split(const std::string& field, char separator) {
    std::vector<std::string> out;
    if (field == "-") {
        return out;
    }
    std::istringstream stream(field);
    for (std::string part; std::getline(stream, part, separator);) {
        out.push_back(part);
    }
    return out;
}

defect_ids::Priority priority_of(const std::string& letter) {
    const auto priority = defect_ids::priority_from_letter(letter.at(0));
    if (!priority) {
        std::cerr << "the vectors use an unknown priority " << letter << '\n';
        std::exit(2);
    }
    return *priority;
}

void test_parse(const std::string& path) {
    const auto rows = read_rows(path, "parse");
    expect(!rows.empty(), "no parse vectors were read");
    for (const Row& row : rows) {
        const auto result = defect_ids::parse(row[0]);
        if (row[1] == "ok") {
            expect(result.has_value() && result->to_string() == row[2], "parse " + row[0]);
        } else {
            expect(!result.has_value() && defect_ids::kind(result.error()) == row[2], "parse " + row[0]);
        }
    }
}

void test_alloc(const std::string& path) {
    const auto rows = read_rows(path, "alloc");
    expect(!rows.empty(), "no alloc vectors were read");
    for (const Row& row : rows) {
        const auto existing = split(row[0], ',');
        auto built = defect_ids::Allocator::from_ids(existing);
        if (row[2] == "ok") {
            expect(built.has_value(), "alloc " + row[0] + " builds");
            const auto id = built->allocate(priority_of(row[1]));
            expect(id.has_value() && id->to_string() == row[3], "alloc " + row[0] + " " + row[1]);
        } else {
            expect(!built.has_value() && defect_ids::kind(built.error()) == row[3], "alloc " + row[0] + " refused");
        }
    }
}

void test_sequences(const std::string& path) {
    const auto rows = read_rows(path, "seq");
    expect(!rows.empty(), "no seq vectors were read");
    for (const Row& row : rows) {
        auto allocator = defect_ids::Allocator::from_ids(split(row[0], ','));
        expect(allocator.has_value(), "seq " + row[0] + " builds");
        std::string got;
        for (const std::string& letter : split(row[1], ',')) {
            const auto id = allocator->allocate(priority_of(letter));
            got += (got.empty() ? "" : ",") + (id ? id->to_string() : std::string{"ERR"});
        }
        expect(got == row[3], "seq " + row[0] + " " + row[1] + " gave " + got);
    }
}

void test_ordering() {
    const auto id = [](const char* text) { return defect_ids::parse(text).value(); };
    expect(id("C9") < id("H1") && id("H1") < id("M1") && id("M1") < id("L1"), "priority order");
    expect(id("H2") < id("H10"), "number order is numeric, not textual");
}

void test_zero_cannot_be_built() {
    expect(!defect_ids::DefectId::make(defect_ids::Priority::high, 0).has_value(), "zero number refused");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: test_defect_ids PATH_TO_VECTORS\n";
        return 2;
    }
    const std::string path = argv[1];
    test_parse(path);
    test_alloc(path);
    test_sequences(path);
    test_ordering();
    test_zero_cannot_be_built();
    std::cout << (failures == 0 ? "all C++ exemplar checks passed\n" : "C++ exemplar checks FAILED\n");
    return failures == 0 ? 0 : 1;
}

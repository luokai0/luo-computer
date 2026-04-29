#include "luo_gate/app.hpp"
#include "luo_gate/security.hpp"

#include <cassert>
#include <iostream>

int main() {
    using namespace luo_gate;

    assert(is_valid_username("Luo"));
    assert(is_valid_username("Kai77") == false);
    assert(is_valid_username("ab") == false);
    assert(is_valid_password("Gate"));

    App app;
    assert(app.register_user("Luo", "Gate"));
    assert(!app.register_user("Luo", "Gate"));
    assert(app.login("Luo", "Gate"));
    assert(app.authenticated());

    app.create_thread("general", "General");
    assert(app.add_message("general", "Luo", "hello"));
    app.set_api_key("search", "alpha");
    app.upload_file("doc.txt", "text");
    app.add_skill("parse", "shared skill");

    const auto state = app.export_state();
    assert(state.find("\"users\":1") != std::string::npos);
    assert(state.find("\"threads\":1") != std::string::npos);
    assert(state.find("\"files\":1") != std::string::npos);
    assert(state.find("\"skills\":1") != std::string::npos);

    std::cout << "luo-gate tests passed\n";
    return 0;
}

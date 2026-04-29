#include "luo_gate/app.hpp"
#include "luo_gate/ui.hpp"

#include <iostream>

int main() {
    luo_gate::App app;
    app.register_user("Luo", "Gate");
    app.login("Luo", "Gate");
    app.create_thread("general", "General Chat");
    app.add_message("general", "Luo", "Welcome to LUO GATE.");
    app.set_api_key("search", "alpha");
    app.upload_file("welcome.txt", "This is the first imported file.");
    app.add_skill("parse", "Shared parsing skill");

    std::cout << luo_gate::render_welcome_screen();
    std::cout << luo_gate::render_login_screen();
    std::cout << luo_gate::render_main_screen(app);
    std::cout << luo_gate::render_api_screen(app);
    return 0;
}

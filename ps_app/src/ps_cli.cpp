#include "ps_core.hpp"
#include <iostream>
#include <string>
int main(){
    // JSON lines permits large test batches without process-per-point overhead.
    std::string line;while(std::getline(std::cin,line))try{
        ps::require(line.size()<=2*1024*1024,"RESOURCE_LIMIT","Request exceeds 2 MiB");
        std::cout<<ps::Json({{"ok",true},{"result",ps::dispatch(ps::Json::parse(line))}}).dump()<<'\n';
    }catch(const ps::Error &e){std::cout<<ps::Json({{"ok",false},{"error",e.detail}}).dump()<<'\n';}
    catch(const std::exception &){std::cout<<ps::Json({{"ok",false},{"error",ps::Error("FORMAT","Malformed or incomplete JSON request").detail}}).dump()<<'\n';}
}

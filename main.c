#include <stdio.h>

typedef struct v2f{
  float x, y;
} v2f;

typedef struct loc{
  v2f a;
} loc;

v2f operv2faddv2f(v2f x, v2f y){
  return (v2f){x.x + y.x, x.y+y.y};
}

void printv2f(v2f a){
  printf("%.2f %.2f\n", a.x, a.y);
}

int main(){
  v2f a = (v2f){1, 2};
  loc b = (loc){(v2f){3, 1}};

  v2f c = a + b.a;

  printv2f(c);
  return 0;
}

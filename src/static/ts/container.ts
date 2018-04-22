type HTMLLikeT = string | HTMLElement | JQuery

interface IContainer<T> {
  add(key: string, obj: T, representation: HTMLLikeT): void;
  addElement(key: string, obj: T, representation: HTMLLikeT): HTMLElement;
  remove(key: string): void;
  removeElement(key: string, obj: T, element: HTMLElement): void;
  clear():  void;
  initEmpty():  void;
  forEach(cb:(key: string, obj: T, elment: HTMLElement)=>void): void;
  contains(key: string):  boolean;
  set(vals: [ string, T, string ][]): void;
}

abstract class BaseContainer<T> implements IContainer<T> {
  objMap: { [ key: string ] : T }
  domMap: { [ key: string ] : HTMLElement }

  constructor (public parent: HTMLElement) {
    this.clear();
  }

  add(key: string, obj: T, representation: HTMLLikeT): void {
    if (this.objMap.hasOwnProperty(key)) { }; //TODO: What do we do?
    this.objMap[key] = obj;
    this.domMap[key] = this.addElement(key, obj, representation);
  };

  remove(key: string): void {
    if (!this.objMap.hasOwnProperty(key)) {
      throw new Error("Key " + key + " not found.");
    }
    this.removeElement(key, this.objMap[key], this.domMap[key]);
    delete this.objMap[key];
    delete this.domMap[key];
  };

  forEach(cb:(key: string, obj: T, elment: HTMLElement)=>void): void {
    for (var key in this.objMap) {
      cb(key, this.objMap[key], this.domMap[key]);
    }
  }

  contains(key: string):  boolean {
    return this.objMap.hasOwnProperty(key);
  }

  clear():  void {
    this.initEmpty();
    this.objMap = {};
    this.domMap = {};   
  }

  set(vals: [ string, T, HTMLLikeT ][]): void {
    this.clear();
    for (var i in vals) {
      this.add(vals[i][0], vals[i][1], vals[i][2]);
    }
  }

  // These are the methods child classes must implement.
  abstract addElement(key: string, obj: T, representation: HTMLLikeT): HTMLElement;
  abstract removeElement(key: string, obj: T, element: HTMLElement): void;
  abstract initEmpty():  void;

}

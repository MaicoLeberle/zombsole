# coding: utf-8
import random

from termcolor import colored

from utils import distance


DEFAULT_COLOR = 'white'
HEALING_RANGE = 3


class World(object):
    '''World where to play the game.'''
    def __init__(self, size, debug=True):
        self.size = size
        self.debug = debug
        self.things = {}
        self.decoration = {}
        self.t = -1
        self.events = []

    def spawn_thing(self, thing, decoration=False):
        '''Add a thing to the world, or to the decoration layer.

           The thing will be spawned into the position it has in its .position
           attribute.
        '''
        if decoration:
            self.decoration[thing.position] = thing
        else:
            other = self.things.get(thing.position)
            if other is None:
                self.things[thing.position] = thing
            else:
                message = u"Can't place %s in a position occupied by %s."
                raise Exception(message % (thing.name, other.name))

    def spawn_in_random(self, things, possible_positions=None,
                        fail_if_cant=True):
        '''Spawn a group of things  in random positions.'''
        # if no positions provided, use all the world positions
        if possible_positions is None:
            spawns = [(x, y)
                      for x in range(self.size[0])
                      for y in range(self.size[1])]
        else:
            spawns = possible_positions[:]

        # remove occupied positions, and shuffle
        spawns = [spawn for spawn in spawns
                  if self.things.get(spawn) is None]
        random.shuffle(spawns)

        # try  to spawn each thing
        for thing in things:
            if spawns:
                thing.position = spawns.pop()
                self.spawn_thing(thing)
            else:
                if fail_if_cant:
                    error = 'Not enough space to spawn %s' % thing.name
                    raise Exception(error)
                else:
                    return

    def event(self, thing, message):
        '''Log an event.'''
        self.events.append((self.t, thing, message))

    def step(self):
        '''Forward one instant of time.'''
        self.t += 1
        actions = self.get_actions()
        random.shuffle(actions)
        self.execute_actions(actions)
        self.clean_dead_things()

    def get_actions(self):
        '''For each thing, call its next_step to get its desired action.'''
        actions = []
        actors = [thing for thing in self.things.values()
                  if thing.ask_for_actions]
        for thing in actors:
            try:
                next_step = thing.next_step(self.things)
                if isinstance(next_step, (tuple, list)) and len(next_step) == 2:
                    action, parameter = next_step
                    actions.append((thing, action, parameter))
                elif next_step is None:
                    self.event(thing, u'idle')
                else:
                    event = u'invalid next_step result: %s' % repr(next_step)
                    raise Exception(event)
            except Exception as err:
                self.event(thing, u'error with next_step: %s' % err.message)
                if self.debug:
                    raise err

        return actions

    def execute_actions(self, actions):
        '''Execute actions, and add their results as events.'''
        for thing, action, parameter in actions:
            try:
                # the method which applies the action is something like:
                # self.thing_ACTION(parameter)
                method = getattr(self, 'thing_' + str(action), None)
                if method:
                    event = method(thing, parameter)
                    self.event(thing, event)
                else:
                    self.event(thing, u'unknown action "%s"' % action)
            except Exception as err:
                event = u'error excuting %s action: %s' % (action, err.message)
                self.event(thing, event)
                if self.debug:
                    raise err

    def clean_dead_things(self):
        '''Remove dead things, and add dead decorations.'''
        dead_things = [thing for thing in self.things.values()
                       if thing.life <= 0]
        for thing in dead_things:
            if thing.dead_decoration is not None:
                thing.dead_decoration.position = thing.position
                self.spawn_thing(thing.dead_decoration,
                                 decoration=True)

            del self.things[thing.position]
            self.event(thing, u'died')

    def thing_move(self, thing, destination):
        '''Apply move action of a thing.

           target: the position to go to.
        '''
        if not isinstance(destination, tuple):
            raise Exception(u'Destination of movement should be a tuple')

        obstacle = self.things.get(destination)
        if obstacle is not None:
            event = u'hit %s with his head' % obstacle.name
        elif distance(thing.position, destination) > 1:
            event = u'tried to walk too fast, but physics forbade it'
        else:
            # we store position in the things, because they need to know it,
            # but also in our dict, for faster access
            self.things[destination] = thing
            del self.things[thing.position]
            thing.position = destination

            event = u'moved to ' + str(destination)

        return event

    def thing_attack(self, thing, target):
        '''Apply attack action of a thing.

           target: the thing to attack.
        '''
        if not isinstance(target, Thing):
            raise Exception(u'Target of attack should be a thing')

        if distance(thing.position, target.position) > thing.weapon.max_range:
            event = u'tried to attack %s, but it is too far for a %s'
            event = event % (target.name, thing.weapon.name)
        else:
            damage = random.randint(*thing.weapon.damage_range)
            target.life -= damage
            event = u'injured %s with a %s' % (target.name, thing.weapon.name)

        return event

    def thing_heal(self, thing, target):
        '''Apply heal action of a thing.

           target: the thing to heal.
        '''
        if not isinstance(target, Thing):
            raise Exception(u'Target of healing should be a thing')

        if distance(thing.position, target.position) > HEALING_RANGE:
            event = u'tried to heal %s, but it is too far away' % target.name
        else:
            # heal avoiding health overflow
            target.life = random.randint(target.life, target.MAX_LIFE)
            event = u'healed ' + target.name

        return event


class Thing(object):
    '''Something in the world.'''
    MAX_LIFE = 1

    def __init__(self, name, icon, color, life, position=None,
                 ask_for_actions=False, dead_decoration=None):
        if len(icon) != 1:
            raise Exception(u'The icon must be a 1 char unicode or string.')

        self.name = name
        self.icon = icon
        self.color = color
        self.life = life
        self.position = position
        self.status = u''
        self.ask_for_actions = ask_for_actions
        self.dead_decoration = dead_decoration

    def next_step(self, things):
        return None

    def draw(self):
        return colored(self.icon, self.color)


class Weapon(object):
    '''Weapon, capable of doing damage to things.'''
    def __init__(self, name, max_range, damage_range):
        self.name = name
        self.max_range = max_range
        self.damage_range = damage_range


class FightingThing(Thing):
    '''Thing that has a weapon.'''
    def __init__(self, name, icon, color, life, weapon, position=None,
                 dead_decoration=None):
        super(FightingThing, self).__init__(name, icon, color, life, position,
                                            ask_for_actions=True,
                                            dead_decoration=dead_decoration)

        self.weapon = weapon

import pygame, time
from random import randint, choice, uniform

pygame.init()

WIDTH, HEIGHT = 640, 480
CONTROL_BAR_HEIGHT = 20
TOTAL_HEIGHT = HEIGHT + CONTROL_BAR_HEIGHT
CONTROL_SPEED = 3
MONSTER_WANDER, MONSTER_CHASE = 1, 2.5
DETECTION_RADIUS = 100
COIN_RESPAWN_DELAY = randint(1500, 10000)
MONSTER_RESPAWN_DELAY = randint(2500, 10000)
MIN_SPAWN_DISTANCE = 100
DASH_DISTANCE, DASH_DURATION, DASH_CD = 50, 100, 2000
INVUL_DURATION = 2000
WIN_SCORE = 40
MAX_MONSTERS, MONSTER_SPAWN_THRESHOLD = 10, 4
NUM_MONSTERS, NUM_COINS = 2, 6

window = pygame.display.set_mode((WIDTH, TOTAL_HEIGHT))
clock = pygame.time.Clock()
robot_img = pygame.image.load("robot.png").convert_alpha()
monster_img = pygame.image.load("monster.png").convert_alpha()
coin_img = pygame.image.load("coin.png").convert_alpha()
door_img = pygame.image.load("door.png").convert_alpha()

controls = {
    pygame.K_LEFT: (-CONTROL_SPEED, 0),
    pygame.K_RIGHT: (CONTROL_SPEED, 0),
    pygame.K_UP: (0, -CONTROL_SPEED),
    pygame.K_DOWN: (0, CONTROL_SPEED),
    pygame.K_a: (-CONTROL_SPEED, 0),
    pygame.K_d: (CONTROL_SPEED, 0),
    pygame.K_w: (0, -CONTROL_SPEED),
    pygame.K_s: (0, CONTROL_SPEED),
}
dash_control = [pygame.K_LSHIFT, pygame.K_RSHIFT]
new_game = pygame.K_F2


class Timer:
    def __init__(self):
        self.start_time = 0
        self.run = False

    def start(self):
        if not self.run:
            self.start_time, self.run = time.time(), True

    def stop(self):
        self.run = False

    def reset(self):
        self.start_time = time.time() if self.run else 0

    def get_time(self):
        if self.run:
            elapsed = time.time() - self.start_time
            return elapsed
        return 0

    def format_time(self):
        elapsed_time = self.get_time()

        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time - int(elapsed_time)) * 1000)

        return f"{minutes:02}:{seconds:02}:{milliseconds:03}"


class Robot(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.points = 0
        self.image = robot_img
        self.original_image = self.image
        self.rect = self.image.get_rect(topleft=(0, HEIGHT - robot_img.get_height()))
        self.mask = pygame.mask.from_surface(self.image)
        self.direction = pygame.math.Vector2(0, 0)

        self.invul = False
        self.invul_duration = INVUL_DURATION
        self.invul_start = 0
        self.blink_interval = 100
        self.last_blink_time = 0
        self.visible = True

        self.dash = False
        self.dash_duration = DASH_DURATION
        self.dash_cd = DASH_CD
        self.dash_start = 0
        self.last_dash = -self.dash_cd
        self.dash_distance = DASH_DISTANCE

        self.cd_bar_width = 50
        self.cd_bar_height = 5

    def activate_invul(self):
        self.invul = True
        self.invul_start = current_time
        self.last_blink_time = current_time
        self.visible = True
        self.image.set_alpha(255)

    def update_invul(self):
        if self.invul:
            elapsed_time = current_time - self.invul_start

            if elapsed_time > self.invul_duration:
                self.invul = False
                self.image.set_alpha(255)
                return
            if current_time - self.last_blink_time > self.blink_interval:
                self.visible = not self.visible
                self.image.set_alpha(255 if self.visible else 0)
                self.last_blink_time = current_time

    def activate_dash(self):
        if not self.dash and current_time - self.last_dash > self.dash_cd:
            self.dash = True
            self.dash_start, self.last_dash = current_time, current_time

    def update_dash(self):
        if self.dash:
            elapsed_time = current_time - self.dash_start

            if elapsed_time < self.dash_duration:
                dash_progress = elapsed_time / self.dash_duration

                if self.direction != pygame.math.Vector2(0, 0):
                    normalized = self.direction.normalize()
                    new_pos = (
                        self.rect.topleft
                        + normalized * self.dash_distance * dash_progress
                    )
                if (
                    WIDTH - self.image.get_width() >= new_pos.x >= 0
                    and HEIGHT - self.image.get_height() >= new_pos.y >= 0
                ):
                    self.rect.topleft = new_pos
            else:
                self.dash = False

    def update(self):
        self.update_invul()
        self.update_dash()

    def draw_cd_bar(self, surface):
        cd_remaining = max(0, self.last_dash + self.dash_cd - current_time)
        cd_percent = cd_remaining / self.dash_cd

        bar_width = int(self.cd_bar_width * cd_percent)
        bar_rect = pygame.Rect(
            self.rect.centerx - self.cd_bar_width / 2,
            self.rect.top - 10,
            bar_width,
            self.cd_bar_height,
        )
        pygame.draw.rect(surface, (255, 0, 0), bar_rect)
        pygame.draw.rect(surface, (0, 255, 0), bar_rect.inflate(0, -self.cd_bar_height))

    def move(self, vx, vy):
        self.rect.x = max(0, min(self.rect.x + vx, WIDTH - self.image.get_width()))
        self.rect.y = max(0, min(self.rect.y + vy, HEIGHT - self.image.get_height()))


class Door(pygame.sprite.Sprite):
    def __init__(self, robot):
        super().__init__()
        self.image = door_img
        self.rect = self.image.get_rect(
            topleft=(
                randint(0, WIDTH - self.image.get_width()),
                randint(0, HEIGHT - self.image.get_height()),
            )
        )
        self.mask = pygame.mask.from_surface(self.image)


class Monster(pygame.sprite.Sprite):
    def __init__(self, robot):
        super().__init__()
        self.image = monster_img.copy()
        self.original_image = self.image.copy()
        self.rect = self.image.get_rect(
            topleft=(
                randint(0, WIDTH - self.image.get_width()),
                randint(0, HEIGHT - self.image.get_height()),
            )
        )
        self.mask = pygame.mask.from_surface(self.image)
        self.robot = robot
        self.speed = uniform(0.5, MONSTER_WANDER)
        self.direction = choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.time_since_direction_change, self.direction_change_interval = (
            0,
            randint(50, 150),
        )
        self.respawn_delay = MONSTER_RESPAWN_DELAY
        self.active = True
        self.fade_alpha, self.fadein_time = 0, 1000
        self.deactivated_time = None
        self.last_respawn_time = 0
        self.grace_period = 500

    def spawn(self):
        while True:
            spawn_x = randint(0, WIDTH - self.image.get_width())
            spawn_y = randint(0, HEIGHT - self.image.get_height())
            new_rect = self.image.get_rect(topleft=(spawn_x, spawn_y))

            distance = (
                (new_rect.centerx - self.robot.rect.centerx) ** 2
                + (new_rect.centery - self.robot.rect.centery) ** 2
            ) ** 0.5
            if distance > MIN_SPAWN_DISTANCE:
                self.rect.topleft = (spawn_x, spawn_y)
                break

        self.active = False
        self.image.set_alpha(0)
        self.last_respawn_time = current_time

    def update(self):
        if not self.active:
            self.fade_in()
        else:
            self.check_collision()
            self.move_monster()

    def fade_in(self):
        if self.deactivated_time is None:
            self.deactivated_time = current_time

        time_since_deactivated = current_time - self.deactivated_time
        if time_since_deactivated > self.respawn_delay:
            fade_duration = time_since_deactivated - self.respawn_delay
            if fade_duration < self.fadein_time:
                self.fade_alpha = min(255, (fade_duration / self.fadein_time) * 255)
                self.image.set_alpha(self.fade_alpha)
            else:
                self.image.set_alpha(255)
                self.active = True
                self.deactivated_time = None

    def check_collision(self):
        if current_time - self.last_respawn_time > self.grace_period:
            if pygame.sprite.collide_mask(self, self.robot) and not self.robot.invul:
                self.robot.points = max(0, self.robot.points - 1)
                self.robot.activate_invul()
                self.active = False
                self.deactivated_time = current_time
                self.image.set_alpha(0)

    def move_monster(self):
        distance_to_robot = (
            self.rect.centerx - self.robot.rect.centerx,
            self.rect.centery - self.robot.rect.centery,
        )
        distance = (distance_to_robot[0] ** 2 + distance_to_robot[1] ** 2) ** 0.5

        if distance < DETECTION_RADIUS:
            self.speed = MONSTER_CHASE
            direction_to_robot = pygame.math.Vector2(
                self.robot.rect.center
            ) - pygame.math.Vector2(self.rect.center)

            if direction_to_robot.length() > 0:
                direction_to_robot.scale_to_length(self.speed)
                self.rect.move_ip(direction_to_robot)
        else:
            self.speed = MONSTER_WANDER
            self.rect.move_ip(
                self.direction[0] * self.speed, self.direction[1] * self.speed
            )

            self.time_since_direction_change += 1
            if self.time_since_direction_change > self.direction_change_interval:
                self.direction = choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                self.speed = uniform(0.5, MONSTER_WANDER)
                self.time_since_direction_change, self.direction_change_interval = (
                    0,
                    randint(50, 150),
                )

            self.rect.x = max(0, min(self.rect.x, WIDTH - self.image.get_width()))
            self.rect.y = max(0, min(self.rect.y, HEIGHT - self.image.get_height()))


class Coin(pygame.sprite.Sprite):
    def __init__(self, robot):
        super().__init__()
        self.image = coin_img
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.robot = robot
        self.respawn_time, self.coin_respawn_delay = 0, COIN_RESPAWN_DELAY
        self.active = True
        self.spawn()

    def spawn(self):
        max_attempts = 100
        for _ in range(max_attempts):
            self.rect.topleft = (
                randint(0, WIDTH - self.image.get_width()),
                randint(0, HEIGHT - self.image.get_height()),
            )
            if not pygame.sprite.collide_mask(self, self.robot):
                self.active = True
                return
        self.active = False

    def update(self):
        if (
            not self.active
            and current_time - self.respawn_time > self.coin_respawn_delay
        ):
            self.spawn()

    def collect(self):
        self.respawn_time, self.coin_respawn_delay, self.active = (
            current_time,
            COIN_RESPAWN_DELAY,
            False,
        )


class Game:
    def __init__(self):
        self.timer = Timer()
        self.timer.start()
        self.control = pygame.font.SysFont("Arial", 20, bold=True)
        self.font = pygame.font.SysFont("Arial", 30)
        self.win = pygame.font.SysFont("Arial", 40, bold=True)
        self.initialize_game()
        self.run()

    def initialize_game(self, num_monsters=NUM_MONSTERS, num_coins=NUM_COINS):
        self.timer.reset()
        self.robot = Robot()
        self.monsters = pygame.sprite.Group(
            Monster(self.robot) for _ in range(num_monsters)
        )
        self.coins = pygame.sprite.Group(Coin(self.robot) for _ in range(num_coins))
        self.last_monster_spawn_score = 0
        self.door, self.game_over = None, False

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == new_game:
                    self.initialize_game()

    def spawn_monster(self):
        if len(self.monsters) < MAX_MONSTERS:
            monster = Monster(self.robot)
            monster.spawn()
            self.monsters.add(monster)

    def remove_monster(self):
        if len(self.monsters) > 2:
            self.monsters.sprites()[-1].kill()

    def spawn_door(self):
        self.door = Door(self.robot)

    def check_win_condition(self):
        if self.robot.points >= WIN_SCORE and not self.door:
            self.spawn_door()
        if self.door and pygame.sprite.collide_mask(self.door, self.robot):
            self.game_over = True

    def increase_difficulty(self):
        if (
            self.robot.points % MONSTER_SPAWN_THRESHOLD == 0
            and self.robot.points > self.last_monster_spawn_score
        ):
            self.spawn_monster()
            self.last_monster_spawn_score = self.robot.points

        if self.robot.points < self.last_monster_spawn_score - MONSTER_SPAWN_THRESHOLD:
            self.remove_monster()
            self.last_monster_spawn_score -= MONSTER_SPAWN_THRESHOLD

    def update_coins(self):
        for coin in self.coins:
            if coin.active and pygame.sprite.collide_mask(coin, self.robot):
                coin.collect()
                self.robot.points = max(0, self.robot.points + 1)

    def draw_controls(self):
        if not self.game_over:
            control_str = "controls: w/a/s/d or arrow keys to move, shift to dash"
        else:
            control_str = "press f2 for a new game"

        control_text = self.control.render(control_str, True, (255, 255, 255))
        window.blit(
            control_text,
            (
                (WIDTH - control_text.get_width()) / 2,
                HEIGHT + (CONTROL_BAR_HEIGHT - control_text.get_height()) / 2,
            ),
        )

    def draw_robot(self):
        if self.robot.dash:
            oval_width, oval_height = robot_img.get_width(), robot_img.get_height()
            oval_rect = pygame.Rect(
                self.robot.rect.centerx - oval_width / 2,
                self.robot.rect.centery - oval_height / 2,
                oval_width,
                oval_height,
            )
            pygame.draw.ellipse(window, (255, 215, 0), oval_rect)
        window.blit(self.robot.image, self.robot.rect.topleft)
        self.robot.draw_cd_bar(window)

    def draw_coins(self):
        for coin in self.coins:
            if coin.active:
                window.blit(coin.image, coin.rect.topleft)

    def draw_monsters(self):
        self.monsters.draw(window)

    def draw_door(self):
        if self.door:
            window.blit(self.door.image, self.door.rect.topleft)
            if not self.game_over:
                door_text = self.font.render(
                    "Door is open! Enter to win!", True, (0, 255, 0)
                )

                text_x = self.door.rect.centerx - door_text.get_width()
                text_y = self.door.rect.top - door_text.get_height() - 5

                text_x, text_y = max(0, text_x), max(0, text_y)
                if text_x + door_text.get_width() > WIDTH:
                    text_x = WIDTH - door_text.get_width()

                window.blit(door_text, (text_x, text_y))

    def draw_score(self):
        score_text = self.font.render(f"Points: {self.robot.points}", True, (255, 0, 0))
        window.blit(score_text, (500, 0))

    def draw_timer(self):
        timer_text = self.font.render(self.timer.format_time(), True, (255, 255, 255))
        window.blit(timer_text, (500, 30))

    def draw_game_over(self):
        win_text = self.win.render("Congratulations! You win!", True, (0, 255, 0))
        window.blit(
            win_text,
            (
                (WIDTH - win_text.get_width()) / 2,
                (HEIGHT - win_text.get_height()) / 2,
            ),
        )

    def draw_window(self):
        window.fill((194, 176, 162))
        pygame.draw.rect(
            window,
            (0, 0, 0),
            (0, HEIGHT, WIDTH, CONTROL_BAR_HEIGHT),
        )

        self.draw_controls()
        self.draw_robot()
        self.draw_coins()
        self.draw_monsters()
        self.draw_door()
        self.draw_score()
        self.draw_timer()

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def move_robot(self):
        pressed = pygame.key.get_pressed()
        total_x, total_y = 0, 0

        for key, v in controls.items():
            if pressed[key]:
                total_x += v[0]
                total_y += v[1]
        if total_x != 0 or total_y != 0:
            self.robot.direction = pygame.math.Vector2(total_x, total_y).normalize()
            self.robot.move(total_x, total_y)
        if any(pressed[key] for key in dash_control):
            self.robot.activate_dash()

    def run(self):
        while True:
            global current_time
            current_time = pygame.time.get_ticks()
            self.check_events()

            if not self.game_over:
                self.move_robot()
                self.monsters.update()
                self.robot.update()
                self.update_coins()
                self.coins.update()
                self.increase_difficulty()
                self.check_win_condition()
                self.draw_window()

            clock.tick(60)


Game()

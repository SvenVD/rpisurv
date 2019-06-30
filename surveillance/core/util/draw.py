import logging
import pygame

logger = logging.getLogger('l_default')

def init(resolution):
    resolution_width=int(resolution[0])
    resolution_height=int(resolution[1])
    pygame.init()
    surface = pygame.display.set_mode((resolution_width, resolution_height))
    pygame.mouse.set_visible(False)
    return surface


def blank_screen(absposx,absposy,width,height,surface):
    logger.debug("blanking the screen")
    surface.fill(pygame.Color("black"))
    #If the surface was an image you should draw over the images
    placeholder(absposx,absposy,width,height,"images/blank.png",surface)

def placeholder(absposx,absposy,width,height,background_img_path,surface):
    """This function creates a new placeholder"""
    logger.debug("Drawing placeholder with coordinates: " + str(absposx) + ", " + str( absposy) + " and width: " + str(width) +  " height: " + str(height) + " with image " + str(background_img_path) )
    background_img = pygame.image.load(background_img_path)
    background_img = pygame.transform.scale(background_img, (width, height))
    surface.blit(background_img, (absposx, absposy))
    refresh()
    return background_img

def check_keypress():
    try:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_a or event.key == pygame.K_KP_DIVIDE or event.key == pygame.K_BACKSPACE:
                    logger.debug("Keypress 'a' or 'q' or 'backspace' or 'keypad /' detected.")
                    return "end_event"
                if event.key == pygame.K_n or event.key == pygame.K_SPACE or event.key == pygame.K_KP_PLUS:
                    logger.debug("Keypress 'n' or 'space' or 'keypad +' detected.")
                    return "next_event"
                if event.key == pygame.K_r or event.key == pygame.K_KP_PERIOD or event.key == pygame.K_COMMA:
                    logger.debug("Keypress 'r' or ',' or 'keypad .' detected")
                    return "resume_rotation"
                if event.key == pygame.K_p or event.key == pygame.K_KP_MULTIPLY:
                    logger.debug("Keypress 'p' or 'keypad *' detected")
                    return "pause_rotation"
                for numeric_key_counter, key in enumerate([pygame.K_F1,pygame.K_F2,pygame.K_F3,pygame.K_F4,pygame.K_F5,pygame.K_F6,pygame.K_F7,pygame.K_F8,pygame.K_F9,pygame.K_F10,pygame.K_F11,pygame.K_F12]):
                    if event.key == key:
                        logger.debug("Keypress 'F" + str(numeric_key_counter + 1) + "' detected")
                        return numeric_key_counter
                for numeric_key_counter, key in enumerate([pygame.K_KP0,pygame.K_KP1,pygame.K_KP2,pygame.K_KP3,pygame.K_KP4,pygame.K_KP5,pygame.K_KP6,pygame.K_KP7,pygame.K_KP8,pygame.K_KP9]):
                    if event.key == key:
                        logger.debug("Keypress 'keypad " + str(numeric_key_counter + 1) + "' detected")
                        return numeric_key_counter
                else:
                    return None
    except pygame.error as e:
        logger.debug("Exception " + repr(e))
        exit(0)

def refresh():
    pygame.display.flip()


def destroy():
    pygame.quit()

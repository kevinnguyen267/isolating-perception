(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_2 - block
		green_1 - block
		green_2 - block
		orange_1 - block
		orange_2 - block
		purple_1 - block
		purple_2 - block
		red_1 - block
		red_2 - block
		yellow_1 - block
		yellow_2 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable green_2)
		(on orange_2 green_2)
		(on yellow_2 orange_2)
		(clear yellow_2)

		(ontable purple_1)
		(on red_2 purple_1)
		(on orange_1 red_2)
		(clear orange_1)

		(ontable blue_2)
		(on yellow_1 blue_2)
		(on blue_1 yellow_1)
		(clear blue_1)

		(ontable purple_2)
		(on green_1 purple_2)
		(on red_1 green_1)
		(clear red_1)
	)
	(:goal (and (handempty robot)
		(ontable green_2)
		(on yellow_2 green_2)
		(on purple_1 yellow_2)
		(clear purple_1)

		(ontable yellow_1)
		(on orange_1 yellow_1)
		(on red_2 orange_1)
		(clear red_2)

		(ontable green_1)
		(on orange_2 green_1)
		(clear orange_2)

		(ontable blue_2)
		(on blue_1 blue_2)
		(clear blue_1)

		(ontable purple_2)
		(on red_1 purple_2)
		(clear red_1)
	))
)